# Kaseya Quote Manager MCP Server

An [MCP](https://modelcontextprotocol.io) server for the [Kaseya Quote Manager](https://www.kaseya.com/products/quote-manager/)
API (v1), the quoting and procurement tool MSPs use to quote, sell and order hardware, software
and services. It lets an AI agent read quotes with their sections and lines, sales orders with
lines and payments, purchase orders with lines and costs, suppliers, the product catalog, and
customers with their contacts and addresses. The API is read-only, so every tool is too.

- Transport: MCP Streamable HTTP at `POST /mcp`, health probe at `GET /health`
- Stateless and multi-tenant: credentials arrive on every request as HTTP headers and are
  never stored; every tool is listed from the first `tools/list`
- Also provides three MCP prompts: `quote-pipeline-review`, `quote-detail` (quote_number),
  `purchasing-summary`
- Python 3.12, [uv](https://docs.astral.sh/uv/), FastMCP, httpx
- License: Apache-2.0, Copyright 2026 MSPbots.ai

## Authentication headers

| Header | Required | Type | Default | Allowed values | Description | Example |
|---|---|---|---|---|---|---|
| `X-Kaseya-Quote-Manager-Api-Key` | Yes | string | none | - | Kaseya Quote Manager API key | `your-api-key` |

Where to get it: in Kaseya Quote Manager open **My account (profile icon) > Developer API**.

How the key is sent: every call goes to `https://api.kaseyaquotemanager.com/v1/...` with the key in
the `apiKey` request header (never in the URL, so it stays out of access logs).

A request to `/mcp` without the header gets HTTP 401.

## Tools

All tools return a JSON string. Lists take `page` (from 1) and `pageSize` (max 100) and return
`{count, page, has_more, next_page, offset, next_offset}`; most also take `modifiedAfter` (ISO date-time) to return only
records changed since then. Lists also take `offset` (0-based record position, overrides `page`):
pass `next_offset` from the previous result to continue, because when a page is cut to fit the
response size limit, `next_offset` starts right after the last record returned, while the rest of
that page is on no other page number. Every `_get` tool takes **id**.

| Area | Tools |
|---|---|
| Overview | `kqm_navigate` (**domain**: sales, procurement, catalog, crm, org), `kqm_status` |
| Sales | `kqm_quote_list` (quoteNumber), `kqm_quote_get`, `kqm_quote_section_list` (quoteID), `kqm_quote_section_get`, `kqm_quote_line_list` (quoteSectionID), `kqm_quote_line_get`, `kqm_sales_order_list` (orderNumber), `kqm_sales_order_get`, `kqm_sales_order_line_list` (salesOrderID), `kqm_sales_order_line_get`, `kqm_sales_order_payment_list` (salesOrderID), `kqm_sales_order_payment_get` |
| Procurement | `kqm_purchase_order_list` (orderNumber), `kqm_purchase_order_get`, `kqm_purchase_order_line_list` (purchaseOrderID), `kqm_purchase_order_line_get`, `kqm_purchase_order_cost_list` (purchaseOrderID), `kqm_purchase_order_cost_get`, `kqm_supplier_list`, `kqm_supplier_get`, `kqm_product_supplier_list` (productID), `kqm_product_supplier_get` |
| Catalog | `kqm_product_list` (manufacturerPartNumber), `kqm_product_get`, `kqm_product_image_list` (productID), `kqm_category_list`, `kqm_category_get`, `kqm_brand_list`, `kqm_brand_get` |
| CRM | `kqm_customer_list`, `kqm_customer_get`, `kqm_customer_address_list` (customerID), `kqm_customer_address_get`, `kqm_contact_list` (customerID), `kqm_contact_get` |
| Organisation | `kqm_employee_list`, `kqm_employee_get`, `kqm_warehouse_list`, `kqm_warehouse_get` |

Errors come back as a JSON envelope instead of an exception:

```json
{"error": {"code": "unauthorized", "message": "Kaseya Quote Manager returned HTTP 401 for quote", "retryable": false}}
```

`code` is one of `not_configured`, `unauthorized`, `not_found`, `invalid_argument`,
`rate_limited`, `upstream_error`. Requests are retried with backoff on 429, 5xx and network
errors. Kaseya Quote Manager allows 60 calls per minute and 20,000 per day.

## Run locally

```bash
uv sync
uv run python -m kaseya_quote_manager_mcp          # listens on 0.0.0.0:8080
```

or with Docker:

```bash
docker build --platform linux/amd64 -t kaseya-quote-manager-mcp:dev .
docker run --rm -p 8080:8080 kaseya-quote-manager-mcp:dev
```

Configuration (environment variables, all optional): `MCP_HTTP_HOST` (default `0.0.0.0`),
`MCP_HTTP_PORT` (default `8080`), `LOG_LEVEL` (default `INFO`). Credentials are never read
from the environment.

## Testing example

```bash
# list tools
curl -s http://localhost:8080/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "X-Kaseya-Quote-Manager-Api-Key: your-api-key" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'

# quotes changed this month
curl -s http://localhost:8080/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "X-Kaseya-Quote-Manager-Api-Key: your-api-key" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"kqm_quote_list","arguments":{"modifiedAfter":"2026-10-01T00:00:00Z"}}}'
```

Unit tests (no network access needed):

```bash
uv run pytest
```

## Delivery notes

- **Tool count (41) and prompts (3).** Kept as is because the names are an existing contract; the
  parameters of every tool match the earlier version and the official API, plus `offset` on the
  list tools (handled here, see paging above).
- **API source.** The official OpenAPI document is published at
  `https://api.kaseyaquotemanager.com/docs/v1/swagger.json` (API Reference v1, 39 read-only
  endpoints); the getting-started guide is in the Kaseya Quote Manager help center.
- **Paging.** The API returns plain arrays with no total; `has_more` is true when a page comes
  back full, and `pageSize` is capped at the API's maximum of 100.
- **All tools are read-only** and annotated as such, matching the API.

## License

Apache License 2.0 - see [LICENSE](LICENSE) and [NOTICE](NOTICE).
