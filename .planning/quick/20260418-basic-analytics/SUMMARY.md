---
id: 20260418-basic-analytics
date: 2026-04-18
mode: quick
status: complete
---

# Basic Analytics — Summary

## What changed

Added server-side usage event logging and a gated admin dashboard. No PII (no IP, no user-agent, no cookies persisted to analytics).

### Files

- **`app/database.py`** — new `usage_events` table created in `init_database()`; helpers `log_usage_event()` and `get_usage_stats()`.
- **`app/routes.py`** — instrumented all 5 exit points in `index()` POST; new `/admin/analytics` endpoint.
- **`app/templates/admin_analytics.html`** — standalone dashboard (no base.html — avoids Plausible + AdSense on admin page).
- **`CLAUDE.md`** — documented `ANALYTICS_TOKEN` env var and the analytics surface.

## Event taxonomy

| status | error_detail | Trigger |
|---|---|---|
| success | — | Cached PDF served |
| success | — | Fresh PDF generated + served |
| error | `no_station` | Empty station field + empty search |
| error | `station_not_found` | Search term didn't match |
| error | `invalid_input` | Year/month/station_id validation failure |
| error | `pdf_missing` | Subprocess ran but PDF not created |
| error | `pdf_empty` | PDF created but 0 bytes |

## Admin endpoint

```
GET /admin/analytics?token=<ANALYTICS_TOKEN>
```

Behavior:
- `ANALYTICS_TOKEN` env var unset → `503 {"error": "analytics_not_configured"}`
- Token missing or mismatched → `401 {"error": "unauthorized"}` (uses `hmac.compare_digest` for constant-time comparison)
- Correct token → HTML dashboard: total/24h/7d/30d counts, success/error totals, top stations (30d), recent events (last 100)

## Verified

- DB layer: `log_usage_event` + `get_usage_stats` exercised with success + error events, returns correct aggregates.
- `/admin/analytics`:
  - 503 when env var unset
  - 401 with no token and wrong token
  - 200 with HTML containing expected data when correct token
- POST `/` instrumentation:
  - Bad station_id (`'abc'`) → `invalid_input` event with station_id preserved
  - Empty station + empty search → `no_station`
  - Empty station + unknown search → `station_not_found`
  - Out-of-range year → `invalid_input`

## Deploy notes

1. Set `ANALYTICS_TOKEN` in CapRover app config (random string — not committed). Without it the endpoint returns 503.
2. New table is created automatically on first request to any route that triggers `init_database()` (happens at container startup via `run.py`).
3. No migration concerns — `CREATE TABLE IF NOT EXISTS` is idempotent.

## Relationship to existing Plausible

`base.html` already loads Plausible (self-hosted at `plausible.mattmanuel.ca`). Those two surfaces answer different questions:

| | Plausible | `usage_events` |
|---|---|---|
| Source | client JS | server-side |
| Blocked by ad-blockers | Yes | No |
| Sees cached PDF serves | No (pageviews only) | Yes |
| Sees validation errors | No | Yes |
| Has station_id per event | No (without custom events) | Yes |

## Out of scope

- No retention/cleanup job — `usage_events` grows unbounded. Add a cron-style sweep if volume becomes a concern (~unlikely at current traffic).
- `/api/generate_quick` is intentionally not instrumented (it already has `--skip_logging` semantics and is for embedded/widget usage).
- No data export (CSV/JSON). Easy to add via query parameter on the admin endpoint if needed later.
