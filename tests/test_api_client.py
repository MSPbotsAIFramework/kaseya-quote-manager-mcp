# Copyright 2026 MSPbots.ai
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Request shapes, paging, retries and tool behaviour against a mocked Quote Manager API."""

import json

import httpx
import pytest

from kaseya_quote_manager_mcp import api_client
from kaseya_quote_manager_mcp.api_client import QuoteManagerClient, QuoteManagerCredentials, QuoteManagerError
from kaseya_quote_manager_mcp.server import _credentials_var, create_mcp_server
from kaseya_quote_manager_mcp.tools.navigation import DOMAINS

CREDS = QuoteManagerCredentials("key-123")


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    async def instant(_seconds):
        return None

    monkeypatch.setattr(api_client.asyncio, "sleep", instant)


class Recorder:
    """Mock transport: replies by method + path below /v1/."""

    def __init__(self, routes=None, default=None):
        self.requests: list[httpx.Request] = []
        self.routes = routes or {}
        self.default = default if default is not None else []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        path = request.url.path.removeprefix("/v1/")
        reply = self.routes.get(f"{request.method} {path}", self.routes.get(path, self.default))
        if callable(reply):
            return reply(request)
        return httpx.Response(200, json=reply)


async def _call(monkeypatch, recorder: Recorder, tool: str, args: dict):
    http = httpx.AsyncClient(transport=httpx.MockTransport(recorder))
    monkeypatch.setattr(api_client, "_get_shared_http_client", lambda: http)
    ctx = _credentials_var.set(CREDS)
    try:
        content, _ = await create_mcp_server().call_tool(tool, args)
    finally:
        _credentials_var.reset(ctx)
    return json.loads(content[0].text)


def _client(recorder: Recorder) -> QuoteManagerClient:
    return QuoteManagerClient(CREDS, httpx.AsyncClient(transport=httpx.MockTransport(recorder)))


async def test_api_key_header_not_in_url():
    rec = Recorder()
    await _client(rec).get("quote", {"page": 1})
    request = rec.requests[0]
    assert request.headers["apikey"] == "key-123"
    assert str(request.url) == "https://api.kaseyaquotemanager.com/v1/quote?page=1"
    assert "key-123" not in str(request.url)


async def test_get_is_retried_on_5xx_and_429():
    replies = iter([httpx.Response(502), httpx.Response(429, headers={"Retry-After": "1"}), httpx.Response(200, json=[])])
    rec = Recorder({"quote": lambda r: next(replies)})
    assert await _client(rec).get("quote") == []
    assert len(rec.requests) == 3


async def test_errors_map_to_envelopes(monkeypatch):
    rec = Recorder({"quote/9": lambda r: httpx.Response(404, json={"message": "Quote not found"}), "quote": lambda r: httpx.Response(401)})
    missing = await _call(monkeypatch, rec, "kqm_quote_get", {"id": 9})
    assert missing["error"]["code"] == "not_found" and missing["error"]["message"].endswith("Quote not found")
    denied = await _call(monkeypatch, rec, "kqm_quote_list", {})
    assert denied["error"]["code"] == "unauthorized"


async def test_list_paging_and_filters(monkeypatch):
    rec = Recorder({"quote": [{"id": i} for i in range(25)]})
    result = await _call(monkeypatch, rec, "kqm_quote_list", {"quoteNumber": "QO1", "page": 2, "pageSize": 25, "modifiedAfter": "2026-10-01"})
    params = rec.requests[0].url.params
    assert (params["quoteNumber"], params["page"], params["pageSize"], params["modifiedAfter"]) == ("QO1", "2", "25", "2026-10-01")
    assert (result["count"], result["page"], result["has_more"], result["next_page"]) == (25, 2, True, 3)


async def test_short_page_is_the_last(monkeypatch):
    rec = Recorder({"supplier": [{"id": 1}]})
    result = await _call(monkeypatch, rec, "kqm_supplier_list", {})
    assert rec.requests[0].url.params["pageSize"] == "100"
    assert result == {"suppliers": [{"id": 1}], "count": 1, "page": 1, "has_more": False, "offset": 0}


async def test_category_list_is_unpaged(monkeypatch):
    rec = Recorder({"category": [{"id": 1, "parentID": None}, {"id": 2, "parentID": 1}]})
    result = await _call(monkeypatch, rec, "kqm_category_list", {})
    assert rec.requests[0].url.params == httpx.QueryParams() and result["count"] == 2


@pytest.mark.parametrize(
    "tool,args,path,param",
    [
        ("kqm_quote_section_list", {"quoteID": 5}, "quotesection", "quoteID"),
        ("kqm_quote_line_list", {"quoteSectionID": 6}, "quoteline", "quoteSectionID"),
        ("kqm_sales_order_line_list", {"salesOrderID": 7}, "salesorderline", "salesOrderID"),
        ("kqm_sales_order_payment_list", {"salesOrderID": 7}, "salesorderpayment", "salesOrderID"),
        ("kqm_purchase_order_line_list", {"purchaseOrderID": 8}, "purchaseorderline", "purchaseOrderID"),
        ("kqm_purchase_order_cost_list", {"purchaseOrderID": 8}, "purchaseordercost", "purchaseOrderID"),
        ("kqm_product_supplier_list", {"productID": 9}, "productsupplier", "productID"),
        ("kqm_product_image_list", {"productID": 9}, "productimage", "productID"),
        ("kqm_customer_address_list", {"customerID": 3}, "customeraddress", "customerID"),
        ("kqm_contact_list", {"customerID": 3}, "contact", "customerID"),
        ("kqm_product_list", {"manufacturerPartNumber": "ABC-1"}, "product", "manufacturerPartNumber"),
        ("kqm_purchase_order_list", {"orderNumber": "PO9"}, "purchaseorder", "orderNumber"),
        ("kqm_sales_order_list", {"orderNumber": "SO9"}, "salesorder", "orderNumber"),
    ],
)
async def test_child_list_filters(monkeypatch, tool, args, path, param):
    rec = Recorder()
    await _call(monkeypatch, rec, tool, args)
    request = rec.requests[0]
    assert request.url.path == f"/v1/{path}" and request.url.params[param] == str(args[param])


@pytest.mark.parametrize("name", sorted({t for _, tools in DOMAINS.values() for t in tools if t.endswith("_get")}))
async def test_every_get_tool_reads_by_id(monkeypatch, name):
    rec = Recorder(default={"id": 42})
    assert await _call(monkeypatch, rec, name, {"id": 42}) == {"id": 42}
    assert rec.requests[0].url.path.endswith("/42") and rec.requests[0].method == "GET"


async def test_status(monkeypatch):
    rec = Recorder({"employee": [{"id": 1}]})
    result = await _call(monkeypatch, rec, "kqm_status", {})
    assert result["connected"] is True and result["read_only_api"] is True
    assert rec.requests[0].url.params["pageSize"] == "1"


async def test_navigate(monkeypatch):
    result = await _call(monkeypatch, Recorder(), "kqm_navigate", {"domain": "sales"})
    assert "kqm_quote_line_get" in result["tools"]


async def test_non_json_error_body():
    rec = Recorder({"quote": lambda r: httpx.Response(400, text="Bad request: page must be positive")})
    with pytest.raises(QuoteManagerError) as e:
        await _client(rec).get("quote")
    assert "page must be positive" in e.value.message


# --- Page-number paging that survives truncation -------------------------------------------
# Quote Manager pages by page + pageSize only. offset reads the page that holds a record
# position and skips the records before it; next_offset continues right after the last
# record returned, also when a page is cut to fit the response size limit.

PAGED_TOOLS = [
    ("kqm_quote_list", "quote", "quotes"),
    ("kqm_quote_section_list", "quotesection", "sections"),
    ("kqm_quote_line_list", "quoteline", "lines"),
    ("kqm_sales_order_list", "salesorder", "sales_orders"),
    ("kqm_sales_order_line_list", "salesorderline", "lines"),
    ("kqm_sales_order_payment_list", "salesorderpayment", "payments"),
    ("kqm_purchase_order_list", "purchaseorder", "purchase_orders"),
    ("kqm_purchase_order_line_list", "purchaseorderline", "lines"),
    ("kqm_purchase_order_cost_list", "purchaseordercost", "costs"),
    ("kqm_supplier_list", "supplier", "suppliers"),
    ("kqm_product_supplier_list", "productsupplier", "product_suppliers"),
    ("kqm_product_list", "product", "products"),
    ("kqm_product_image_list", "productimage", "images"),
    ("kqm_brand_list", "brand", "brands"),
    ("kqm_customer_list", "customer", "customers"),
    ("kqm_customer_address_list", "customeraddress", "addresses"),
    ("kqm_contact_list", "contact", "contacts"),
    ("kqm_employee_list", "employee", "employees"),
    ("kqm_warehouse_list", "warehouse", "warehouses"),
]


def _paging_api(total: int, big: bool = False) -> Recorder:
    """A fake API that pages ``total`` records by page number + page size, like the real one."""
    filler = {f"field{i}": f"{i}-" + "x" * 150 for i in range(30)} if big else {}
    records = [{"id": n, **filler} for n in range(total)]

    def reply(request: httpx.Request) -> httpx.Response:
        page = int(request.url.params.get("page", 1))
        size = int(request.url.params.get("pageSize", 100))
        return httpx.Response(200, json=records[(page - 1) * size : page * size])

    return Recorder(default=reply)


async def _walk(monkeypatch, rec: Recorder, tool: str, key: str, first: dict) -> list[int]:
    ids: list[int] = []
    args = dict(first)
    for _ in range(100):
        result = await _call(monkeypatch, rec, tool, args)
        assert "retry_page_size" not in result or "next_offset" not in result
        ids += [r["id"] for r in result[key]]
        if "next_offset" not in result:
            assert result["has_more"] is False
            return ids
        args = {"pageSize": first["pageSize"], "offset": result["next_offset"]}
    raise AssertionError("did not finish")


@pytest.mark.parametrize("tool,path,key", PAGED_TOOLS)
async def test_cut_pages_walked_by_next_offset_return_every_record_once(monkeypatch, tool, path, key):
    rec = _paging_api(35, big=True)
    first = await _call(monkeypatch, rec, tool, {"pageSize": 10})
    assert first["truncated"] is True and first["count"] < 10  # the page really is cut
    assert "retry_page_size" not in first and first["next_offset"] == first["count"]
    assert await _walk(monkeypatch, rec, tool, key, {"pageSize": 10}) == list(range(35))


@pytest.mark.parametrize("tool,path,key", PAGED_TOOLS)
async def test_cut_pages_walked_from_a_later_page(monkeypatch, tool, path, key):
    rec = _paging_api(35, big=True)
    assert await _walk(monkeypatch, rec, tool, key, {"page": 3, "pageSize": 10}) == list(range(20, 35))


@pytest.mark.parametrize("tool,path,key", PAGED_TOOLS)
@pytest.mark.parametrize("offset,page,first_id", [(13, 2, 13), (20, 3, 20), (0, 1, 0)])
async def test_offset_reads_the_page_that_holds_it(monkeypatch, tool, path, key, offset, page, first_id):
    rec = _paging_api(35)
    result = await _call(monkeypatch, rec, tool, {"pageSize": 10, "offset": offset})
    params = rec.requests[0].url.params
    assert rec.requests[0].url.path == f"/v1/{path}"
    assert (params["page"], params["pageSize"]) == (str(page), "10")
    assert [r["id"] for r in result[key]] == list(range(first_id, page * 10))
    assert result["offset"] == offset and result["next_offset"] == page * 10 and result["has_more"] is True


@pytest.mark.parametrize("tool,path,key", PAGED_TOOLS)
async def test_offset_past_the_end(monkeypatch, tool, path, key):
    result = await _call(monkeypatch, _paging_api(35), tool, {"pageSize": 10, "offset": 100})
    assert result[key] == [] and result["count"] == 0 and result["has_more"] is False
    assert "next_offset" not in result and "next_page" not in result


@pytest.mark.parametrize("tool,path,key", PAGED_TOOLS)
async def test_offset_wins_over_page(monkeypatch, tool, path, key):
    rec = _paging_api(35)
    result = await _call(monkeypatch, rec, tool, {"page": 3, "pageSize": 10, "offset": 5})
    assert rec.requests[0].url.params["page"] == "1"
    assert [r["id"] for r in result[key]] == list(range(5, 10))


@pytest.mark.parametrize("tool,path,key", PAGED_TOOLS)
async def test_page_only_call_sends_the_same_request(monkeypatch, tool, path, key):
    rec = _paging_api(35)
    result = await _call(monkeypatch, rec, tool, {"page": 2, "pageSize": 10})
    assert str(rec.requests[0].url) == f"https://api.kaseyaquotemanager.com/v1/{path}?page=2&pageSize=10"
    assert [r["id"] for r in result[key]] == list(range(10, 20))
    assert (result["page"], result["next_page"], result["offset"], result["next_offset"]) == (2, 3, 10, 20)

    rec = _paging_api(35)
    result = await _call(monkeypatch, rec, tool, {})
    assert str(rec.requests[0].url) == f"https://api.kaseyaquotemanager.com/v1/{path}?page=1&pageSize=100"
    assert result["count"] == 35 and result["has_more"] is False and "next_offset" not in result
