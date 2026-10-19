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
"""Shared argument types, list / record helpers and the error-handling wrapper."""

import logging
import time
from collections.abc import Awaitable, Callable
from typing import Annotated, Any

from mcp.types import ToolAnnotations
from pydantic import Field

from .._json import dump_json_capped, error_envelope
from ..api_client import QuoteManagerClient, QuoteManagerError
from ..config import MAX_PAGE_SIZE

logger = logging.getLogger("kaseya_quote_manager_mcp.tools")

ClientFactory = Callable[[], QuoteManagerClient | None]

READ_ONLY = ToolAnnotations(readOnlyHint=True, idempotentHint=True, openWorldHint=True)
LOCAL = ToolAnnotations(readOnlyHint=True, idempotentHint=True, openWorldHint=False)

NOT_CONFIGURED = error_envelope(
    "not_configured", "Kaseya Quote Manager credentials are missing for this request (X-Kaseya-Quote-Manager-Api-Key).", False
)

RecordId = Annotated[int, Field(description="Record id.", ge=1)]
ParentId = Annotated[int | None, Field(description="Only records of this parent id.", ge=1)]
Page = Annotated[int | None, Field(description="Page number, starting at 1.", ge=1)]
PageSize = Annotated[int | None, Field(description=f"Records per page (default and max {MAX_PAGE_SIZE}).", ge=1, le=MAX_PAGE_SIZE)]
ModifiedAfter = Annotated[str | None, Field(description="ISO 8601 date-time: only records changed after it.")]


def compact(values: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in values.items() if v is not None and v != ""}


async def list_page(client: QuoteManagerClient, path: str, key: str, params: dict[str, Any], page: int | None, page_size: int | None) -> dict:
    """GET a list (a plain JSON array) and add paging hints."""
    number, size = page or 1, page_size or MAX_PAGE_SIZE
    payload = await client.get(path, compact(params) | {"page": number, "pageSize": size})
    rows = payload if isinstance(payload, list) else []
    full = len(rows) >= size
    return compact({key: rows, "count": len(rows), "page": number, "has_more": full, "next_page": number + 1 if full else None})


async def run_tool(
    name: str,
    client_factory: ClientFactory,
    action: Callable[[QuoteManagerClient], Awaitable[Any]],
) -> str:
    """Resolve the caller's client, run ``action``, and always return a string.

    Errors never escape as exceptions: they become the standard error envelope.
    """
    client = client_factory()
    if client is None:
        return NOT_CONFIGURED
    started = time.monotonic()
    try:
        value = await action(client)
    except QuoteManagerError as e:
        logger.info("tool=%s outcome=error status=%s ms=%d", name, e.status_code, _ms(started))
        return e.to_envelope()
    except ValueError as e:
        logger.info("tool=%s outcome=invalid_argument ms=%d", name, _ms(started))
        return error_envelope("invalid_argument", str(e), False)
    except Exception as e:  # noqa: BLE001 - tools must never raise
        logger.warning("tool=%s outcome=unexpected error=%s ms=%d", name, type(e).__name__, _ms(started))
        return error_envelope("upstream_error", f"Unexpected error: {type(e).__name__}", True)
    logger.info("tool=%s outcome=ok ms=%d", name, _ms(started))
    if value is None:
        value = {"done": True}
    return value if isinstance(value, str) else dump_json_capped(value)


def _ms(started: float) -> int:
    return int((time.monotonic() - started) * 1000)
