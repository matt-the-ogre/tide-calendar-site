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

**Effort:** Small. **Impact:** Only matters during a CHS API outage.

---

## Reference: relevant code

- Import + filter + normalization: `app/canadian_station_sync.py`
  (`normalize_station`, `fetch_canadian_stations_from_api`, `construct_place_name`)
- Search + display formatting: `app/database.py`
  (`search_stations_by_country`, `get_popular_stations_by_country`, `format_display_name`)
- Frontend rendering: `app/templates/index.html` (autocomplete dropdown + popular table)
- Tests: `app/test_canadian_station_sync.py`, `app/test_station_search.py`
