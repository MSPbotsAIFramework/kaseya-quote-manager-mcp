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
"""Organisation: employees and warehouses."""

from typing import Any

from mcp.server.fastmcp import FastMCP

from ..api_client import QuoteManagerClient
from ._common import ClientFactory, ModifiedAfter, Page, PageSize, READ_ONLY, RecordId, list_page, run_tool


def register(mcp: FastMCP, client_factory: ClientFactory) -> None:
    @mcp.tool(annotations=READ_ONLY)
    async def kqm_employee_list(
        page: Page = None,
        pageSize: PageSize = None,
    ) -> str:
        """List employees: name, email, active flag, visibility, last login."""

        async def action(client: QuoteManagerClient) -> dict:
            return await list_page(client, "employee", "employees", {}, page, pageSize)

        return await run_tool("kqm_employee_list", client_factory, action)

    @mcp.tool(annotations=READ_ONLY)
    async def kqm_employee_get(id: RecordId) -> str:
        """Get one employee."""

        async def action(client: QuoteManagerClient) -> Any:
            return await client.get(f"employee/{id}")

        return await run_tool("kqm_employee_get", client_factory, action)

    @mcp.tool(annotations=READ_ONLY)
    async def kqm_warehouse_list(
        page: Page = None,
        pageSize: PageSize = None,
        modifiedAfter: ModifiedAfter = None,
    ) -> str:
        """List warehouses: name, email, address."""

        async def action(client: QuoteManagerClient) -> dict:
            return await list_page(client, "warehouse", "warehouses", {"modifiedAfter": modifiedAfter}, page, pageSize)

        return await run_tool("kqm_warehouse_list", client_factory, action)

    @mcp.tool(annotations=READ_ONLY)
    async def kqm_warehouse_get(id: RecordId) -> str:
        """Get one warehouse."""

        async def action(client: QuoteManagerClient) -> Any:
            return await client.get(f"warehouse/{id}")

        return await run_tool("kqm_warehouse_get", client_factory, action)
