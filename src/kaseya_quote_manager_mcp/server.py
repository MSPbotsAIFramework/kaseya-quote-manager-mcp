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
"""FastMCP factory and the per-request credential middleware."""

import contextvars
import re
import uuid
from collections.abc import Callable

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from .api_client import QuoteManagerClient, QuoteManagerCredentials
from .config import Settings

HEADER_API_KEY = "X-Kaseya-Quote-Manager-Api-Key"
REQUIRED_HEADERS = [HEADER_API_KEY]

_PLACEHOLDER = re.compile(r"^\$\{.*\}$")

# Per-request isolation: the middleware sets these for the duration of one
# HTTP request and resets them in `finally`. Nothing credential-related is
# ever stored at module level.
_credentials_var: contextvars.ContextVar[QuoteManagerCredentials | None] = contextvars.ContextVar("kqm_credentials", default=None)
request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("kqm_request_id", default="-")

INSTRUCTIONS = (
    "Kaseya Quote Manager is the MSP's quoting and procurement tool: quotes "
    "(made of sections and lines) become sales orders (lines, payments); "
    "purchase orders buy from suppliers; products, brands and categories form "
    "the catalog; customers have contacts and addresses. The API is read-only.\n"
    "Usage:\n"
    "- A quote in full: kqm_quote_list(quoteNumber) -> kqm_quote_section_list(quoteID) "
    "-> kqm_quote_line_list(quoteSectionID).\n"
    "- An order: kqm_sales_order_list(orderNumber) -> kqm_sales_order_line_list / "
    "kqm_sales_order_payment_list(salesOrderID).\n"
    "- Purchasing: kqm_purchase_order_list -> kqm_purchase_order_line_list / "
    "kqm_purchase_order_cost_list(purchaseOrderID); kqm_supplier_list.\n"
    "- Lists page with page (from 1) and pageSize (max 100); modifiedAfter "
    "(ISO date) returns only records changed since then.\n"
    "Records refer to each other by id (customerID, ownerEmployeeID, productID ...); "
    "use the matching _get tool to resolve one. The API allows 60 calls per minute."
)


def get_client_from_context() -> QuoteManagerClient | None:
    """The client for the current request, or None outside a request."""
    credentials = _credentials_var.get()
    if credentials is None:
        return None
    return QuoteManagerClient(credentials)


def _clean(value: str | None) -> str | None:
    text = (value or "").strip()
    if not text or _PLACEHOLDER.match(text):
        return None
    return text


class GatewayCredentialsMiddleware:
    """Reads the Quote Manager API key on /mcp requests into the request context; 401 when missing."""

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or not scope.get("path", "").startswith("/mcp"):
            await self.app(scope, receive, send)
            return

        request = Request(scope)
        api_key = _clean(request.headers.get(HEADER_API_KEY))
        if not api_key:
            await JSONResponse(
                {"error": "Missing credentials", "message": f"Missing header(s): {HEADER_API_KEY}", "required_headers": REQUIRED_HEADERS},
                status_code=401,
            )(scope, receive, send)
            return

        request_id = (request.headers.get("x-request-id") or "").strip()[:64] or uuid.uuid4().hex[:12]
        creds_token = _credentials_var.set(QuoteManagerCredentials(api_key))
        rid_token = request_id_var.set(request_id)
        try:
            await self.app(scope, receive, send)
        finally:
            _credentials_var.reset(creds_token)
            request_id_var.reset(rid_token)


def create_mcp_server(settings: Settings | None = None) -> FastMCP:
    """Build the FastMCP server and register every tool and prompt."""
    mcp = FastMCP(
        name="kaseya-quote-manager-mcp",
        instructions=INSTRUCTIONS,
        # The service sits behind the gateway, so Host is never localhost;
        # DNS-rebinding protection would reject those requests with 421.
        transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
        stateless_http=True,
    )

    client_factory: Callable[[], QuoteManagerClient | None] = get_client_from_context

    from . import prompts
    from .tools import catalog, crm, navigation, org, procurement, sales

    for module in (navigation, sales, procurement, catalog, crm, org):
        module.register(mcp, client_factory)
    prompts.register(mcp)

    return mcp
