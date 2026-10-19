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
"""Catalog: products, product images, categories and brands."""

from typing import Annotated, Any

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from ..api_client import QuoteManagerClient
from ._common import ClientFactory, ModifiedAfter, Page, PageSize, READ_ONLY, RecordId, list_page, run_tool


def register(mcp: FastMCP, client_factory: ClientFactory) -> None:
    @mcp.tool(annotations=READ_ONLY)
    async def kqm_product_list(
        manufacturerPartNumber: Annotated[str | None, Field(description="Manufacturer part number (MPN).")] = None,
        page: Page = None,
        pageSize: PageSize = None,
        modifiedAfter: ModifiedAfter = None,
    ) -> str:
        """List products: number, MPN, title, type, brand, category, price, retail price, status flags."""

        async def action(client: QuoteManagerClient) -> dict:
            return await list_page(client, "product", "products", {"manufacturerPartNumber": manufacturerPartNumber, "modifiedAfter": modifiedAfter}, page, pageSize)

        return await run_tool("kqm_product_list", client_factory, action)

    @mcp.tool(annotations=READ_ONLY)
    async def kqm_product_get(id: RecordId) -> str:
        """Get one product with its prices, weight, brand, category and recurring terms."""

        async def action(client: QuoteManagerClient) -> Any:
            return await client.get(f"product/{id}")

        return await run_tool("kqm_product_get", client_factory, action)

    @mcp.tool(annotations=READ_ONLY)
    async def kqm_product_image_list(
        productID: Annotated[int | None, Field(description="Only images of this product id.", ge=1)] = None,
        page: Page = None,
        pageSize: PageSize = None,
    ) -> str:
        """List product image URLs by product number."""

        async def action(client: QuoteManagerClient) -> dict:
            return await list_page(client, "productimage", "images", {"productID": productID}, page, pageSize)

        return await run_tool("kqm_product_image_list", client_factory, action)

    @mcp.tool(annotations=READ_ONLY)
    async def kqm_category_list() -> str:
        """List product categories (a tree: parentID), with type and display order."""

        async def action(client: QuoteManagerClient) -> dict:
            rows = await client.get("category")
            rows = rows if isinstance(rows, list) else []
            return {"categories": rows, "count": len(rows)}

        return await run_tool("kqm_category_list", client_factory, action)

    @mcp.tool(annotations=READ_ONLY)
    async def kqm_category_get(id: RecordId) -> str:
        """Get one product category."""

        async def action(client: QuoteManagerClient) -> Any:
            return await client.get(f"category/{id}")

        return await run_tool("kqm_category_get", client_factory, action)

    @mcp.tool(annotations=READ_ONLY)
    async def kqm_brand_list(
        page: Page = None,
        pageSize: PageSize = None,
        modifiedAfter: ModifiedAfter = None,
    ) -> str:
        """List product brands: id, name, image file."""

        async def action(client: QuoteManagerClient) -> dict:
            return await list_page(client, "brand", "brands", {"modifiedAfter": modifiedAfter}, page, pageSize)

        return await run_tool("kqm_brand_list", client_factory, action)

    @mcp.tool(annotations=READ_ONLY)
    async def kqm_brand_get(id: RecordId) -> str:
        """Get one brand."""

        async def action(client: QuoteManagerClient) -> Any:
            return await client.get(f"brand/{id}")

        return await run_tool("kqm_brand_get", client_factory, action)
