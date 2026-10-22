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
"""tools/list and prompts snapshot, annotations and error-envelope mapping. No network access."""

import asyncio
import json

import pytest

from kaseya_quote_manager_mcp.api_client import QuoteManagerError
from kaseya_quote_manager_mcp.server import INSTRUCTIONS, create_mcp_server
from kaseya_quote_manager_mcp.tools.navigation import DOMAINS

PAGED = {"page", "pageSize", "offset"}
MOD = {"modifiedAfter"}

# Tool name -> its full parameter set. Names and parameters are a public
# contract: existing agents and tenant connections depend on them.
EXPECTED_PARAMS: dict[str, set[str]] = {
    "kqm_navigate": {"domain"},
    "kqm_status": set(),
    "kqm_quote_list": {"quoteNumber"} | PAGED | MOD,
    "kqm_quote_section_list": {"quoteID"} | PAGED,
    "kqm_quote_line_list": {"quoteSectionID"} | PAGED,
    "kqm_sales_order_list": {"orderNumber"} | PAGED | MOD,
    "kqm_sales_order_line_list": {"salesOrderID"} | PAGED | MOD,
    "kqm_sales_order_payment_list": {"salesOrderID"} | PAGED | MOD,
    "kqm_purchase_order_list": {"orderNumber"} | PAGED | MOD,
    "kqm_purchase_order_line_list": {"purchaseOrderID"} | PAGED | MOD,
    "kqm_purchase_order_cost_list": {"purchaseOrderID"} | PAGED | MOD,
    "kqm_supplier_list": PAGED | MOD,
    "kqm_product_supplier_list": {"productID"} | PAGED | MOD,
    "kqm_product_list": {"manufacturerPartNumber"} | PAGED | MOD,
    "kqm_product_image_list": {"productID"} | PAGED,
    "kqm_category_list": set(),
    "kqm_brand_list": PAGED | MOD,
    "kqm_customer_list": PAGED | MOD,
    "kqm_customer_address_list": {"customerID"} | PAGED | MOD,
    "kqm_contact_list": {"customerID"} | PAGED | MOD,
    "kqm_employee_list": PAGED,
    "kqm_warehouse_list": PAGED | MOD,
}
GET_TOOLS = [
    "quote", "quote_section", "quote_line", "sales_order", "sales_order_line", "sales_order_payment",
    "purchase_order", "purchase_order_line", "purchase_order_cost", "supplier", "product_supplier",
    "product", "category", "brand", "customer", "customer_address", "contact", "employee", "warehouse",
]
EXPECTED_PARAMS |= {f"kqm_{n}_get": {"id"} for n in GET_TOOLS}
EXPECTED_REQUIRED = {n: ({"id"} if n.endswith("_get") else {"domain"} if n == "kqm_navigate" else set()) for n in EXPECTED_PARAMS}


@pytest.fixture(scope="module")
def tools():
    return {t.name: t for t in asyncio.run(create_mcp_server().list_tools())}


def test_tool_names_are_stable(tools):
    assert set(tools) == set(EXPECTED_PARAMS)
    assert len(tools) == 41


@pytest.mark.parametrize("name", sorted(EXPECTED_PARAMS))
def test_params(tools, name):
    schema = tools[name].inputSchema
    assert set(schema["properties"]) == EXPECTED_PARAMS[name]
    assert set(schema.get("required", [])) == EXPECTED_REQUIRED[name]


@pytest.mark.parametrize("name", sorted(EXPECTED_PARAMS))
def test_description_budget(tools, name):
    description = (tools[name].description or "").strip()
    assert description, f"{name} has no description"
    assert len(description) <= 500
    assert len(description.splitlines()[0]) <= 100


@pytest.mark.parametrize("name", sorted(EXPECTED_PARAMS))
def test_every_tool_is_read_only(tools, name):
    annotations = tools[name].annotations
    assert annotations is not None and annotations.readOnlyHint is True and not annotations.destructiveHint
    assert (annotations.openWorldHint is False) is (name == "kqm_navigate")


def test_page_size_is_capped(tools):
    assert tools["kqm_quote_list"].inputSchema["properties"]["pageSize"]["anyOf"][0]["maximum"] == 100


def test_prompts_are_stable():
    prompts = {p.name: p for p in asyncio.run(create_mcp_server().list_prompts())}
    assert set(prompts) == {"quote-pipeline-review", "quote-detail", "purchasing-summary"}
    assert [a.name for a in prompts["quote-detail"].arguments if a.required] == ["quote_number"]


def test_prompt_renders_quote_number():
    result = asyncio.run(create_mcp_server().get_prompt("quote-detail", {"quote_number": "QO123"}))
    text = result.messages[0].content.text
    assert "'QO123'" in text and "kqm_quote_section_list" in text


def test_navigate_lists_every_tool():
    listed = {tool for _, names in DOMAINS.values() for tool in names}
    assert listed | {"kqm_navigate", "kqm_status"} == set(EXPECTED_PARAMS)


def test_instructions_budget():
    assert len(INSTRUCTIONS) <= 1500
    assert "\n" in INSTRUCTIONS


@pytest.mark.parametrize(
    "status,code,retryable",
    [
        (401, "unauthorized", False),
        (403, "unauthorized", False),
        (404, "not_found", False),
        (400, "invalid_argument", False),
        (429, "rate_limited", True),
        (500, "upstream_error", True),
        (0, "upstream_error", True),
    ],
)
def test_error_envelope(status, code, retryable):
    envelope = json.loads(QuoteManagerError(status, "boom").to_envelope())
    assert envelope == {"error": {"code": code, "message": "boom", "retryable": retryable}}


def test_tool_without_credentials_returns_not_configured():
    content, _ = asyncio.run(create_mcp_server().call_tool("kqm_quote_list", {}))
    assert json.loads(content[0].text)["error"]["code"] == "not_configured"
