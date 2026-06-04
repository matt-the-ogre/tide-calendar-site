# Canadian Station Search — Follow-up Work

Context: the station name search/autocomplete was overhauled so visitors can find
Canadian stations by name (see commit "Fix Canadian station name search"). That
change relaxed the CHS import filter (now keeps any station with `wlp-hilo`
predictions, ~1,076 vs 71 before) and indexed the CHS `alternativeName` (common
name) into a new `alternative_name` column so searches match either the official
or common name, displaying e.g. `Pender Harbour (ḵalpilin), BC`.

The items below are known limitations that were intentionally left out of that
change. They are independent and can be tackled in any order.

---

## 1. Province inference is inaccurate

**Problem:** When a CHS `officialName` has no province code, `construct_place_name()`
in `app/canadian_station_sync.py` guesses the province from longitude. The guess is
coarse and sometimes wrong.

**Evidence:** Station 06380 displays as `Holman (Ulukhaktok), MB`. Ulukhaktok is in
the Northwest Territories (NT), not Manitoba (MB) — the longitude band for "prairie"
swallowed it.

**Proposed fix:** The CHS per-station metadata endpoint returns an authoritative
`provinceCode`:

```
GET https://api.iwls-sine.azure.cloud-nuage.dfo-mpo.gc.ca/api/v1/stations/{id}/metadata
-> { ..., "provinceCode": "BC", ... }
```

Use it instead of the longitude heuristic.

**Cost/trade-off:** The bulk `/stations` list response does **not** include
`provinceCode`, so this requires one extra call per station (~1,076 calls) at
container startup. Options to keep startup fast:
- Fetch metadata only for stations whose name lacks a province code (the minority).
- Cache provinceCode in the DB and only refetch for new/unknown stations.
- Run it as a periodic maintenance script rather than at every startup.

**Related:** The `province` **column** is also left empty (`''`) for stations whose
province was inferred from longitude rather than parsed from the name — the inferred
value only lands inside `place_name` (e.g. `"ḵalpilin, BC"`), not the column. So
`get_station_info()` returns `''` for province on those rows. `format_display_name()`
compensates by splitting the suffix out of `place_name`, but a proper fix would
populate the column from the authoritative `provinceCode` above and keep the two
in sync.

**Effort:** Medium. **Impact:** Cosmetic (wrong province label), but visible.

---

## 2. Diacritic-insensitive search

**Problem:** Search is a plain SQLite `LIKE` substring match, which is not
Unicode-fold-aware. Typing the plain ASCII "kalpilin" does **not** match the
official name "ḵalpilin" (the `ḵ` is U+1E35, "k with line below").

**Current state:** Users can still find station 07837 by typing "pender" (the common
name) or "ḵalpilin" exactly, so this is a nice-to-have, not a blocker.

**Proposed fix:** Add a normalized/folded search column (strip diacritics to ASCII,
e.g. via `unicodedata` NFKD + combining-mark removal, plus a small custom map for
characters like `ḵ`→`k` that NFKD doesn't decompose) and match against it. Populate
it on import alongside `place_name`/`alternative_name`.

**Effort:** Medium. **Impact:** Helps users who type the Indigenous name phonetically
in ASCII.

---

## 3. Messy CHS `alternativeName` values

**Problem:** Some CHS alternate names are duplicated or malformed, which produces
ugly combined display labels. They are still searchable, just unattractive.

**Evidence:**
- 03765 Alert → alt `Dumb Bell Bay, DUMB BELL BAY`
- 09958 Henslung Cove → alt `Parry Passage, B.C., Parry Passage, B.C.`

These render as e.g. `Dumb Bell Bay, DUMB BELL BAY (Alert), NT`.

**Proposed fix:** In `normalize_station()`, clean the alternate name before storing:
de-duplicate repeated segments, collapse `, <SAME UPPERCASED>` echoes, and optionally
skip combining into the display label (still index it for search) when it contains
commas or exceeds a length threshold — fall back to showing just the official name.

**Effort:** Small–Medium. **Impact:** Cosmetic polish for a handful of stations.

---

## 4. Stale CSV fallback (`app/canadian_tide_stations.csv`)

**Problem:** The CSV fallback (used only when the CHS API is unreachable at startup)
still contains the old hand-curated station set and has no `alternative_name` column.
The importer tolerates the missing column (defaults to NULL), so it won't crash — but
if the API is ever down, the site falls back to a much smaller list with no common-name
search.

**Proposed fix:** Regenerate the fallback CSV from a successful live import (all ~1,076
stations including an `alternative_name` column) so the degraded mode closely matches
normal operation. Could be a small maintenance script under `scripts/`.

**Note:** The stale CSV already causes a pre-existing failure in
`scripts/test_multi_country_offline.py` ("Get Canadian station info (Halifax) — Wrong
API source: None") because Halifax is no longer in the curated CSV. Regenerating the
CSV would fix that test too. (Unrelated to the name-search change; these `scripts/`
tests are not run by the new CI job.)

**Effort:** Small. **Impact:** Only matters during a CHS API outage.

---

## 5. Monitor for empty calendars from newly-surfaced stations

**Problem:** Relaxing the import filter to "any station with `wlp-hilo`" added ~1,005
stations. 07837 was verified to have current/forward predictions, but not all of the
newly-included stations were — a truly-defunct one (only historical data) would now be
selectable by name and produce an empty calendar. This is handled gracefully (the
empty-PDF path returns the error template), and was an accepted trade-off, but it
should be watched.

**Proposed action (operational, no code):** After the prod deploy, watch
`/admin/analytics` for an uptick in `error_detail = pdf_empty` / `pdf_missing`. That is
the exact signal that a dead station is now reachable via name search. If a specific
station recurs, either exclude it or fall back to checking prediction availability for
the requested month at import/selection time.

**Effort:** Tiny (watch existing analytics). **Impact:** Catches dead stations early.

---

## 6. Harden `format_display_name()` province split

**Problem:** When no explicit province is passed, `format_display_name()` in
`app/database.py` splits the trailing `", …"` off `place_name` via `rpartition(', ')`
and treats the tail as the province. This is correct today only because
`construct_place_name()` always appends `", PROV"` for aliased (Canadian) stations and
USA stations have no alias (so they return early). If that invariant ever changes, an
official name containing a comma but no province suffix would be mis-split.

**Proposed fix:** Constrain the fallback to a province/state-code shape (e.g. a short
alpha token, or membership in `PROVINCE_CODES`) before treating it as a suffix, or
make `place_name` carry a structured province consistently (see #1).

**Effort:** Small. **Impact:** Defensive; no known trigger today.

---

## 7. (Optional) Consolidate the two `import_canadian_stations_from_csv()`

**Status:** The data inconsistency is **resolved** — both functions now write
`alternative_name`. The `database.py` copy is NOT dead: it is the CSV-only importer
used by the offline maintenance scripts (`scripts/test_canadian_import.py`,
`test_multi_country_offline.py`, `test_lookup_count_preservation.py`), while
`canadian_station_sync.py`'s copy is the API importer (with its own CSV fallback) used
at runtime startup. They serve different purposes, so they are not strictly duplicates.

**Optional cleanup:** If the divergence still feels risky, consolidate the two CSV
readers into one shared helper that both the offline scripts and the runtime fallback
call. Low priority.

**Effort:** Small–Medium. **Impact:** Code clarity only (no functional gap remains).

---

## Reference: relevant code

- Import + filter + normalization: `app/canadian_station_sync.py`
  (`normalize_station`, `fetch_canadian_stations_from_api`, `construct_place_name`)
- Search + display formatting: `app/database.py`
  (`search_stations_by_country`, `get_popular_stations_by_country`, `format_display_name`)
- Frontend rendering: `app/templates/index.html` (autocomplete dropdown + popular table)
- Tests: `app/test_canadian_station_sync.py`, `app/test_station_search.py`
