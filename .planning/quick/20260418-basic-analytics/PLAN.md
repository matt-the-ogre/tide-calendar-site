---
id: 20260418-basic-analytics
date: 2026-04-18
mode: quick
status: complete
---

# Basic Analytics

## Description

Event-level usage tracking: log every request to `/` (form POST) with station, date/time, and success/error status. No PII (no IP, no user-agent). Expose read-only admin endpoint behind a token.

## Decisions (from user)

1. **Coverage**: Log every request — successes, generation errors, AND validation rejects (full funnel).
2. **Hook point**: `app/routes.py` `index()` POST handler only. Not `get_tides.py` (misses cached serves).
3. **Admin surface**: `/admin/analytics?token=<ANALYTICS_TOKEN>` — gated by env var.

## Schema

```sql
CREATE TABLE IF NOT EXISTS usage_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    station_id TEXT,
    station_name TEXT,
    year INTEGER,
    month INTEGER,
    status TEXT NOT NULL,      -- 'success' or 'error'
    error_detail TEXT          -- short reason when status='error'
);
CREATE INDEX IF NOT EXISTS idx_usage_events_timestamp ON usage_events(timestamp);
```

## Tasks

### Task 1 — DB schema + helpers

**Files:** `app/database.py`

- Extend `init_database()` to create `usage_events` table + index on `timestamp`.
- Add `log_usage_event(station_id, station_name, year, month, status, error_detail=None)` — follows the `log_station_lookup` pattern (swallows errors, non-blocking).
- Add `get_usage_stats(recent_limit=50)` — returns dict: `{total, last_24h, last_7d, success_count, error_count, top_stations, recent_events}`.

**Verify:** Python import works; call `log_usage_event` + `get_usage_stats` against local DB.

### Task 2 — Instrument routes

**Files:** `app/routes.py`

Hook `log_usage_event` at every exit path in `index()` POST:
- station missing / not found → status=`error`, detail=`no_station` / `station_not_found`
- form validation failure → status=`error`, detail=`invalid_input`
- cached PDF served → status=`success`
- PDF not created after subprocess → status=`error`, detail=`pdf_missing`
- PDF empty → status=`error`, detail=`pdf_empty`
- fresh PDF served → status=`success`

**Verify:** POST to `/` locally with valid/invalid payloads; sqlite shows events.

### Task 3 — Admin endpoint

**Files:** `app/routes.py`

- `GET /admin/analytics` — read `ANALYTICS_TOKEN` env var.
  - If env var unset → `503 {"error": "analytics_not_configured"}`
  - If `?token=` missing or mismatched → `401`
  - Otherwise → HTML page rendering `get_usage_stats()` as a clean table.

**Verify:** curl with and without correct token; 401/200 behave as expected.

### Task 4 — Docs

**Files:** `CLAUDE.md`

- Add `ANALYTICS_TOKEN` to env var list (local + CapRover).
- One line under "Important Notes" about the new analytics surface.

## Must-haves

- `usage_events` table exists after `init_database()`.
- Every exit path in `index()` POST logs exactly one event.
- `/admin/analytics` is unreachable without the right token.
- No IP address, user-agent, or cookie values stored in the new table.
- Logging failures never break PDF delivery (errors caught, logged only).
