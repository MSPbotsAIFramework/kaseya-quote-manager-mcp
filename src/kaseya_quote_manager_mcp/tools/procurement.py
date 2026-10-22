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
"""Procurement: purchase orders (lines, extra costs), suppliers and which supplier sells which product."""

from typing import Annotated, Any

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from ..api_client import QuoteManagerClient
from ._common import ClientFactory, ModifiedAfter, Offset, Page, PageSize, READ_ONLY, RecordId, list_page, run_tool


def register(mcp: FastMCP, client_factory: ClientFactory) -> None:
    @mcp.tool(annotations=READ_ONLY)
    async def kqm_purchase_order_list(
        orderNumber: Annotated[str | None, Field(description="Purchase order number.")] = None,
        page: Page = None,
        pageSize: PageSize = None,
        modifiedAfter: ModifiedAfter = None,
        offset: Offset = None,
    ) -> str:
        """List purchase orders: number, supplier, warehouse, sales order, type, status, due date, addresses."""

        async def action(client: QuoteManagerClient) -> dict:
            return await list_page(client, "purchaseorder", "purchase_orders", {"orderNumber": orderNumber, "modifiedAfter": modifiedAfter}, page, pageSize, offset)

        return await run_tool("kqm_purchase_order_list", client_factory, action)

    @mcp.tool(annotations=READ_ONLY)
    async def kqm_purchase_order_get(id: RecordId) -> str:
        """Get one purchase order with its supplier, warehouse, status and addresses."""

        async def action(client: QuoteManagerClient) -> Any:
            return await client.get(f"purchaseorder/{id}")

        return await run_tool("kqm_purchase_order_get", client_factory, action)

    @mcp.tool(annotations=READ_ONLY)
    async def kqm_purchase_order_line_list(
        purchaseOrderID: Annotated[int | None, Field(description="Only lines of this purchase order id.", ge=1)] = None,
        page: Page = None,
        pageSize: PageSize = None,
        modifiedAfter: ModifiedAfter = None,
        offset: Offset = None,
    ) -> str:
        """List purchase order lines: product, price, landed cost, quantity ordered / received, serials."""

        async def action(client: QuoteManagerClient) -> dict:
            return await list_page(client, "purchaseorderline", "lines", {"purchaseOrderID": purchaseOrderID, "modifiedAfter": modifiedAfter}, page, pageSize, offset)

        return await run_tool("kqm_purchase_order_line_list", client_factory, action)

    @mcp.tool(annotations=READ_ONLY)
    async def kqm_purchase_order_line_get(id: RecordId) -> str:
        """Get one purchase order line."""

        async def action(client: QuoteManagerClient) -> Any:
            return await client.get(f"purchaseorderline/{id}")

        return await run_tool("kqm_purchase_order_line_get", client_factory, action)

    @mcp.tool(annotations=READ_ONLY)
    async def kqm_purchase_order_cost_list(
        purchaseOrderID: Annotated[int | None, Field(description="Only costs of this purchase order id.", ge=1)] = None,
        page: Page = None,
        pageSize: PageSize = None,
        modifiedAfter: ModifiedAfter = None,
        offset: Offset = None,
    ) -> str:
        """List extra costs on purchase orders (freight, fees): description, amount, tax."""

        async def action(client: QuoteManagerClient) -> dict:
            return await list_page(client, "purchaseordercost", "costs", {"purchaseOrderID": purchaseOrderID, "modifiedAfter": modifiedAfter}, page, pageSize, offset)

        return await run_tool("kqm_purchase_order_cost_list", client_factory, action)

    @mcp.tool(annotations=READ_ONLY)
    async def kqm_purchase_order_cost_get(id: RecordId) -> str:
        """Get one purchase order cost."""

        async def action(client: QuoteManagerClient) -> Any:
            return await client.get(f"purchaseordercost/{id}")

        return await run_tool("kqm_purchase_order_cost_get", client_factory, action)

    @mcp.tool(annotations=READ_ONLY)
    async def kqm_supplier_list(
        page: Page = None,
        pageSize: PageSize = None,
        modifiedAfter: ModifiedAfter = None,
        offset: Offset = None,
    ) -> str:
        """List suppliers: account number, name, email, online ordering and ETA, notes."""

        async def action(client: QuoteManagerClient) -> dict:
            return await list_page(client, "supplier", "suppliers", {"modifiedAfter": modifiedAfter}, page, pageSize, offset)

        return await run_tool("kqm_supplier_list", client_factory, action)

    @mcp.tool(annotations=READ_ONLY)
    async def kqm_supplier_get(id: RecordId) -> str:
        """Get one supplier."""

        async def action(client: QuoteManagerClient) -> Any:
            return await client.get(f"supplier/{id}")

        return await run_tool("kqm_supplier_get", client_factory, action)

    @mcp.tool(annotations=READ_ONLY)
    async def kqm_product_supplier_list(
        productID: Annotated[int | None, Field(description="Only supplier links of this product id.", ge=1)] = None,
        page: Page = None,
        pageSize: PageSize = None,
        modifiedAfter: ModifiedAfter = None,
        offset: Offset = None,
    ) -> str:
        """List product-supplier links: which supplier sells a product, at what cost, with what stock."""

        async def action(client: QuoteManagerClient) -> dict:
            return await list_page(client, "productsupplier", "product_suppliers", {"productID": productID, "modifiedAfter": modifiedAfter}, page, pageSize, offset)

        return await run_tool("kqm_product_supplier_list", client_factory, action)

    @mcp.tool(annotations=READ_ONLY)
    async def kqm_product_supplier_get(id: RecordId) -> str:
        """Get one product-supplier link."""

        async def action(client: QuoteManagerClient) -> Any:
            return await client.get(f"productsupplier/{id}")

        return await run_tool("kqm_product_supplier_get", client_factory, action)
