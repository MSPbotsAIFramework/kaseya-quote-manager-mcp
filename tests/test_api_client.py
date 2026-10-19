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
    assert result == {"suppliers": [{"id": 1}], "count": 1, "page": 1, "has_more": False}


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
