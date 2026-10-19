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
"""Tool discovery (kept for compatibility: every tool is always listed) and the connection check."""

from typing import Annotated, Literal

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from .._json import compact as to_json
from ..api_client import QuoteManagerClient
from ._common import LOCAL, READ_ONLY, ClientFactory, run_tool


def _pair(*names: str) -> list[str]:
    return [f"kqm_{n}_{op}" for n in names for op in ("list", "get")]


DOMAINS: dict[str, tuple[str, list[str]]] = {
    "sales": (
        "Quotes (sections, lines) and sales orders (lines, payments).",
        _pair("quote", "quote_section", "quote_line", "sales_order", "sales_order_line", "sales_order_payment"),
    ),
    "procurement": (
        "Purchase orders (lines, costs), suppliers and product-supplier links.",
        _pair("purchase_order", "purchase_order_line", "purchase_order_cost", "supplier", "product_supplier"),
    ),
    "catalog": ("Products, product images, categories and brands.", _pair("product") + ["kqm_product_image_list"] + _pair("category", "brand")),
    "crm": ("Customers, customer addresses and contacts.", _pair("customer", "customer_address", "contact")),
    "org": ("Employees and warehouses.", _pair("employee", "warehouse")),
}

Domain = Literal["sales", "procurement", "catalog", "crm", "org"]


def register(mcp: FastMCP, client_factory: ClientFactory) -> None:
    @mcp.tool(annotations=LOCAL)
    async def kqm_navigate(domain: Annotated[Domain, Field(description="Area to describe.")]) -> str:
        """Describe the tools of one Quote Manager area. All tools are already callable; this changes nothing."""
        summary, tools = DOMAINS[domain]
        return to_json({"domain": domain, "summary": summary, "tools": tools})

    @mcp.tool(annotations=READ_ONLY)
    async def kqm_status() -> str:
        """Check the Kaseya Quote Manager connection (one small read) and list the areas."""

        async def action(client: QuoteManagerClient) -> dict:
            await client.get("employee", {"page": 1, "pageSize": 1})
            return {"connected": True, "read_only_api": True, "domains": list(DOMAINS)}

        return await run_tool("kqm_status", client_factory, action)
