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
"""CRM: customers, their delivery addresses and contacts."""

from typing import Annotated, Any

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from ..api_client import QuoteManagerClient
from ._common import ClientFactory, ModifiedAfter, Offset, Page, PageSize, READ_ONLY, RecordId, list_page, run_tool


def register(mcp: FastMCP, client_factory: ClientFactory) -> None:
    @mcp.tool(annotations=READ_ONLY)
    async def kqm_customer_list(
        page: Page = None,
        pageSize: PageSize = None,
        modifiedAfter: ModifiedAfter = None,
        offset: Offset = None,
    ) -> str:
        """List customers: account number, name, owner, tax number, billing address, price group, credit."""

        async def action(client: QuoteManagerClient) -> dict:
            return await list_page(client, "customer", "customers", {"modifiedAfter": modifiedAfter}, page, pageSize, offset)

        return await run_tool("kqm_customer_list", client_factory, action)

    @mcp.tool(annotations=READ_ONLY)
    async def kqm_customer_get(id: RecordId) -> str:
        """Get one customer."""

        async def action(client: QuoteManagerClient) -> Any:
            return await client.get(f"customer/{id}")

        return await run_tool("kqm_customer_get", client_factory, action)

    @mcp.tool(annotations=READ_ONLY)
    async def kqm_customer_address_list(
        customerID: Annotated[int | None, Field(description="Only addresses of this customer id.", ge=1)] = None,
        page: Page = None,
        pageSize: PageSize = None,
        modifiedAfter: ModifiedAfter = None,
        offset: Offset = None,
    ) -> str:
        """List customer delivery addresses: contact, address, city, state, country, instructions."""

        async def action(client: QuoteManagerClient) -> dict:
            return await list_page(client, "customeraddress", "addresses", {"customerID": customerID, "modifiedAfter": modifiedAfter}, page, pageSize, offset)

        return await run_tool("kqm_customer_address_list", client_factory, action)

    @mcp.tool(annotations=READ_ONLY)
    async def kqm_customer_address_get(id: RecordId) -> str:
        """Get one customer address."""

        async def action(client: QuoteManagerClient) -> Any:
            return await client.get(f"customeraddress/{id}")

        return await run_tool("kqm_customer_address_get", client_factory, action)

    @mcp.tool(annotations=READ_ONLY)
    async def kqm_contact_list(
        customerID: Annotated[int | None, Field(description="Only contacts of this customer id.", ge=1)] = None,
        page: Page = None,
        pageSize: PageSize = None,
        modifiedAfter: ModifiedAfter = None,
        offset: Offset = None,
    ) -> str:
        """List customer contacts: name, email, phone, mobile, invoice e-mailing, portal logins."""

        async def action(client: QuoteManagerClient) -> dict:
            return await list_page(client, "contact", "contacts", {"customerID": customerID, "modifiedAfter": modifiedAfter}, page, pageSize, offset)

        return await run_tool("kqm_contact_list", client_factory, action)

    @mcp.tool(annotations=READ_ONLY)
    async def kqm_contact_get(id: RecordId) -> str:
        """Get one contact."""

        async def action(client: QuoteManagerClient) -> Any:
            return await client.get(f"contact/{id}")

        return await run_tool("kqm_contact_get", client_factory, action)
