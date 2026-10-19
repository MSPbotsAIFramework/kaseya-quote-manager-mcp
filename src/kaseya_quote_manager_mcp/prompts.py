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
"""Ready-made review prompts (MCP prompts). They only describe work; the tools do it."""

from typing import Annotated

from mcp.server.fastmcp import FastMCP
from pydantic import Field


def register(mcp: FastMCP) -> None:
    @mcp.prompt(name="quote-pipeline-review", description="Summarise open quotes by status and value")
    def quote_pipeline_review() -> str:
        return "\n".join(
            [
                "Summarise the Kaseya Quote Manager sales pipeline.",
                "1. Page through kqm_quote_list (page 1, 2, ... while has_more is true).",
                "2. Count quotes per status.",
                "3. For the larger open quotes, total their lines (kqm_quote_section_list -> kqm_quote_line_list: "
                "price x quantity, plus delivery) to estimate value.",
                "4. Flag open quotes whose expiryDate is within 14 days.",
                "Report: counts and value by status, quotes expiring soon, and the largest open quotes.",
            ]
        )

    @mcp.prompt(name="quote-detail", description="Break one quote down into sections, lines and customer")
    def quote_detail(quote_number: Annotated[str, Field(description="Quote number, e.g. QO12345678.")]) -> str:
        return "\n".join(
            [
                f"Break down quote {quote_number!r}.",
                "1. Find it with kqm_quote_list(quoteNumber=...).",
                "2. Read its customer (kqm_customer_get) and owner (kqm_employee_get).",
                "3. List its sections (kqm_quote_section_list(quoteID)) and each section's lines "
                "(kqm_quote_line_list(quoteSectionID)).",
                "Report the customer, status and expiry, then a table per section (line, product, quantity, price, "
                "discount, optional / recurring) with section and quote totals.",
            ]
        )

    @mcp.prompt(name="purchasing-summary", description="Summarise open purchase orders, costs and supplier exposure")
    def purchasing_summary() -> str:
        return "\n".join(
            [
                "Summarise purchasing in Kaseya Quote Manager.",
                "1. Page through kqm_purchase_order_list and keep orders that are not received or closed.",
                "2. For each, total kqm_purchase_order_line_list (price x quantity, quantity still to receive) "
                "and kqm_purchase_order_cost_list.",
                "3. Resolve suppliers with kqm_supplier_get.",
                "Report open spend per supplier, orders past their due date, and lines still waiting to be received.",
            ]
        )
