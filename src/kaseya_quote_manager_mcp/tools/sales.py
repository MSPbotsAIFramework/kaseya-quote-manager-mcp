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
"""Sales: quotes (sections, lines) and the sales orders they become (lines, payments)."""

from typing import Annotated, Any

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from ..api_client import QuoteManagerClient
from ._common import ClientFactory, ModifiedAfter, Offset, Page, PageSize, READ_ONLY, RecordId, list_page, run_tool


def register(mcp: FastMCP, client_factory: ClientFactory) -> None:
    @mcp.tool(annotations=READ_ONLY)
    async def kqm_quote_list(
        quoteNumber: Annotated[str | None, Field(description="Quote number, e.g. QO12345678.")] = None,
        page: Page = None,
        pageSize: PageSize = None,
        modifiedAfter: ModifiedAfter = None,
        offset: Offset = None,
    ) -> str:
        """List quotes: number, title, status, customer, owner, contact, delivery details, expiry, dates."""

        async def action(client: QuoteManagerClient) -> dict:
            return await list_page(client, "quote", "quotes", {"quoteNumber": quoteNumber, "modifiedAfter": modifiedAfter}, page, pageSize, offset)

        return await run_tool("kqm_quote_list", client_factory, action)

    @mcp.tool(annotations=READ_ONLY)
    async def kqm_quote_get(id: RecordId) -> str:
        """Get one quote: status, customer, owner, contact, delivery charges, Autotask links, expiry."""

        async def action(client: QuoteManagerClient) -> Any:
            return await client.get(f"quote/{id}")

        return await run_tool("kqm_quote_get", client_factory, action)

    @mcp.tool(annotations=READ_ONLY)
    async def kqm_quote_section_list(
        quoteID: Annotated[int | None, Field(description="Only sections of this quote id.", ge=1)] = None,
        page: Page = None,
        pageSize: PageSize = None,
        offset: Offset = None,
    ) -> str:
        """List quote sections: quote id, title, type, line order, multi-choice / selected flags."""

        async def action(client: QuoteManagerClient) -> dict:
            return await list_page(client, "quotesection", "sections", {"quoteID": quoteID}, page, pageSize, offset)

        return await run_tool("kqm_quote_section_list", client_factory, action)

    @mcp.tool(annotations=READ_ONLY)
    async def kqm_quote_section_get(id: RecordId) -> str:
        """Get one quote section."""

        async def action(client: QuoteManagerClient) -> Any:
            return await client.get(f"quotesection/{id}")

        return await run_tool("kqm_quote_section_get", client_factory, action)

    @mcp.tool(annotations=READ_ONLY)
    async def kqm_quote_line_list(
        quoteSectionID: Annotated[int | None, Field(description="Only lines of this quote section id.", ge=1)] = None,
        page: Page = None,
        pageSize: PageSize = None,
        offset: Offset = None,
    ) -> str:
        """List quote lines: product, title, price, quantity, tax, discount, optional / recurring flags."""

        async def action(client: QuoteManagerClient) -> dict:
            return await list_page(client, "quoteline", "lines", {"quoteSectionID": quoteSectionID}, page, pageSize, offset)

        return await run_tool("kqm_quote_line_list", client_factory, action)

    @mcp.tool(annotations=READ_ONLY)
    async def kqm_quote_line_get(id: RecordId) -> str:
        """Get one quote line with its price, tax, discount and recurring terms."""

        async def action(client: QuoteManagerClient) -> Any:
            return await client.get(f"quoteline/{id}")

        return await run_tool("kqm_quote_line_get", client_factory, action)

    @mcp.tool(annotations=READ_ONLY)
    async def kqm_sales_order_list(
        orderNumber: Annotated[str | None, Field(description="Sales order number.")] = None,
        page: Page = None,
        pageSize: PageSize = None,
        modifiedAfter: ModifiedAfter = None,
        offset: Offset = None,
    ) -> str:
        """List sales orders: number, customer, contact, quote, status, fulfillment, delivery, totals."""

        async def action(client: QuoteManagerClient) -> dict:
            return await list_page(client, "salesorder", "sales_orders", {"orderNumber": orderNumber, "modifiedAfter": modifiedAfter}, page, pageSize, offset)

        return await run_tool("kqm_sales_order_list", client_factory, action)

    @mcp.tool(annotations=READ_ONLY)
    async def kqm_sales_order_get(id: RecordId) -> str:
        """Get one sales order with status, fulfillment, customer, delivery and payment surcharge."""

        async def action(client: QuoteManagerClient) -> Any:
            return await client.get(f"salesorder/{id}")

        return await run_tool("kqm_sales_order_get", client_factory, action)

    @mcp.tool(annotations=READ_ONLY)
    async def kqm_sales_order_line_list(
        salesOrderID: Annotated[int | None, Field(description="Only lines of this sales order id.", ge=1)] = None,
        page: Page = None,
        pageSize: PageSize = None,
        modifiedAfter: ModifiedAfter = None,
        offset: Offset = None,
    ) -> str:
        """List sales order lines: product, price, cost, quantity, tax, discount, serial numbers."""

        async def action(client: QuoteManagerClient) -> dict:
            return await list_page(client, "salesorderline", "lines", {"salesOrderID": salesOrderID, "modifiedAfter": modifiedAfter}, page, pageSize, offset)

        return await run_tool("kqm_sales_order_line_list", client_factory, action)

    @mcp.tool(annotations=READ_ONLY)
    async def kqm_sales_order_line_get(id: RecordId) -> str:
        """Get one sales order line."""

        async def action(client: QuoteManagerClient) -> Any:
            return await client.get(f"salesorderline/{id}")

        return await run_tool("kqm_sales_order_line_get", client_factory, action)

    @mcp.tool(annotations=READ_ONLY)
    async def kqm_sales_order_payment_list(
        salesOrderID: Annotated[int | None, Field(description="Only payments of this sales order id.", ge=1)] = None,
        page: Page = None,
        pageSize: PageSize = None,
        modifiedAfter: ModifiedAfter = None,
        offset: Offset = None,
    ) -> str:
        """List sales order payments: order id, payment type, amount, transaction id, dates."""

        async def action(client: QuoteManagerClient) -> dict:
            return await list_page(client, "salesorderpayment", "payments", {"salesOrderID": salesOrderID, "modifiedAfter": modifiedAfter}, page, pageSize, offset)

        return await run_tool("kqm_sales_order_payment_list", client_factory, action)

    @mcp.tool(annotations=READ_ONLY)
    async def kqm_sales_order_payment_get(id: RecordId) -> str:
        """Get one sales order payment."""

        async def action(client: QuoteManagerClient) -> Any:
            return await client.get(f"salesorderpayment/{id}")

        return await run_tool("kqm_sales_order_payment_get", client_factory, action)
