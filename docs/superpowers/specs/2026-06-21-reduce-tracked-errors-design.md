# Reduce tracked errors — design

**Date:** 2026-06-21
**Branch:** `feature/reduce-tracked-errors`

## Motivation

Live `usage_events` analytics showed a ~20% error rate (54 of 264 events). Full
prod-DB investigation revealed the headline rate was misleading:

- **38** errors: `unknown_station` for station `00000` via the Quick API — a
  single-day bot/probe burst on 2026-06-11 (not ongoing, not a real user).
- **8** errors: legacy `pdf_missing` — a code path removed in the
  `calendar_service` refactor (commit `48e52f2`); cannot recur.
- **7** errors: `station_not_found` (web) — the only recurring *real-user*
  error: a place typed into the search box that wasn't picked from the
  autocomplete and didn't resolve.
- **1** error: `invalid_input` (year out of range) — negligible.

True server-failure rate (`no_predictions` / `generation_failed` / exception):
**0**. The single `status='error'` bucket conflated bot probes, user friction,
and dead code.

## Changes

### 1. Split client (4xx) vs server (5xx) errors — metric honesty
- `database.CLIENT_ERROR_DETAILS` is the single source of truth: `unknown_station`,
  `station_not_found`, `no_station`, `invalid_input`, `junk_station_id`.
- `get_usage_stats()` returns `client_error_count`, `server_error_count`, and
  `rejected_count` alongside the existing `error_count` (total, unchanged).
- `admin_analytics.html` shows **Errors (4xx client)**, **Errors (5xx server)**,
  and **Rejected (junk)** cards instead of one **Errors** card.

### 2. Short-circuit junk station IDs
- `calendar_service.is_junk_station_id()` → true for all-zeros IDs (`00000`).
- `get_or_generate_pdf()` drops junk *before* the directory lookup, logging
  `status='rejected'`, `error_detail='junk_station_id'`. `rejected` is a third
  top-level status — counted as **neither success nor error**.
- Routes map `junk_station_id` → HTTP 400 (quick API) / "not found, pick from
  dropdown" (web form).

### 3. `station_not_found` UX — safe, unambiguous resolution only
- `get_station_id_by_place_name()` now resolves the two shapes the search box
  invites but that aren't place names — a bare numeric ID, and the autocomplete's
  `Name (12345)` format — **only when they map to a real station** (a typo'd
  digit string falls through to `None`, never a wrong station).
- `index.html` submit handler promotes a bare-numeric search box value into the
  hidden `station_id` field (so the server resolves it and analytics get the real ID).
- No fuzzy/prefix matching (explicitly rejected — silent wrong-station risk).

## Testing
- `is_junk_station_id` and the `get_or_generate_pdf` rejected path —
  `test_calendar_service.py`.
- `get_station_id_by_place_name` digit-ID / `Name (ID)` / unknown-numeric cases —
  `test_station_search.py`.
- `get_usage_stats` client/server/rejected split — `scripts/test_usage_events.py`.
- End-to-end (Flask test client): quick-API junk → 400 + logged `rejected`;
  dashboard renders the new cards; resolver shortcuts work.
