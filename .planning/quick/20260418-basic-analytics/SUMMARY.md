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

- **`app/database.py`** — new `usage_events` table (with `source` column) created in `init_database()`; helpers `log_usage_event()` (accepts `source`) and `get_usage_stats()` (returns web/quick_api split). Retention prune runs on init.
- **`app/routes.py`** — instrumented all 5 exit points in `index()` POST (`source='web'`) and all 5 exit points in `/api/generate_quick` (`source='quick_api'`); new `/admin/analytics` endpoint returning 404 for all unauth access.
- **`app/templates/admin_analytics.html`** — standalone dashboard (no base.html). Shows web/quick_api counts, surfaces DB errors in a banner, includes source column in the recent-events table.
- **`scripts/test_usage_events.py`** — 6 pytest-style assertions covering schema, insert, retention, aggregation, source tagging, and error paths. Follows existing `scripts/test_*.py` convention (runnable standalone).
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
| error | `exception` | Unhandled exception in `/api/generate_quick` |

**Source tag** (new column): `web` for POST to `/`, `quick_api` for `/api/generate_quick`.

## Admin endpoint

```
GET /admin/analytics?token=<ANALYTICS_TOKEN>
```

Behavior:
- Any unauth or unconfigured request → `404` rendering the standard 404 page (invisible to scanners; no endpoint fingerprinting). If `ANALYTICS_TOKEN` is unset but a token was supplied, a warning is logged server-side so the admin can spot the misconfig.
- Correct token → HTML dashboard: total/24h/7d/30d counts, success/error totals, web vs. quick_api breakdown, top stations (30d), recent events with source column (last 100).
- Token comparison uses `hmac.compare_digest` (constant-time).
- If the DB errors out, a red banner surfaces the SQL error at the top of the dashboard instead of silently showing zeros.

## Verified

- Pytest-style test suite at `scripts/test_usage_events.py` (6 tests, all passing):
  - Schema + index present after `init_database()`
  - `log_usage_event` persists correct fields with default `source='web'` and explicit `source='quick_api'`
  - `log_usage_event` swallows DB errors without raising (mirrors `log_station_lookup`)
  - `get_usage_stats` aggregates totals, success/error split, web/quick_api split, top stations filtering, and recent events ordering
  - Retention prunes events older than 365 days on re-init; recent events untouched
  - `get_usage_stats` returns sentinel dict with `error` key on DB failure
- `/admin/analytics`:
  - 404 when env var unset (with or without token)
  - 404 with no token or wrong token when env var set
  - 200 with HTML containing expected data when correct token
- POST `/` instrumentation: all 5 exit paths (`no_station`, `station_not_found`, `invalid_input`, `pdf_missing`, `pdf_empty`, plus success) captured with `source='web'`.
- `/api/generate_quick` instrumentation: all 5 exit paths (`invalid_input` x2, `pdf_missing`, `pdf_empty`, `exception`, plus success) captured with `source='quick_api'`.

## Deploy notes

1. Set `ANALYTICS_TOKEN` in CapRover app config (random string — not committed). Without it the endpoint returns 404 (invisible to scanners). The dashboard is only reachable once both the env var is set and a matching token is supplied via `Authorization: Bearer <token>` header or `?token=<token>` query param.
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

- No data export (CSV/JSON). Easy to add via query parameter on the admin endpoint if needed later.
- No in-app rate limiting on the admin endpoint. CapRover/Cloudflare layer handles this upstream; the token is the primary defense and hmac comparison prevents timing-based brute force.
- No anomaly alerting (e.g. notify on sudden error-rate spike). Manual inspection via the dashboard is sufficient for current traffic.

## Resolved in code-review pass

- **Retention**: events older than 365 days are pruned in `init_database()` on each container startup (runs once at boot via `run.py`).
- **Quick API instrumentation**: `/api/generate_quick` now emits events with `source='quick_api'`. Embed/widget traffic is visible.
- **Fingerprinting**: admin endpoint returns 404 for all failure modes; scanners can't tell the endpoint exists.
- **Silent DB failure**: dashboard now shows a red error banner at the top if `get_usage_stats` returned a sentinel dict.
- **Test coverage**: `scripts/test_usage_events.py` covers schema, insert, retention, aggregation, and error paths. Follows existing `scripts/test_*.py` convention.
