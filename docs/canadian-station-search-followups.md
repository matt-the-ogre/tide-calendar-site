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

## 1. Province inference is inaccurate ✅ FIXED

**Was:** `construct_place_name()` guessed the province from longitude when the CHS
`officialName` had no province code. An audit showed this was far worse than first
assumed:
- **1,075 of 1,076** imported stations had no province in their name, so nearly all
  relied on the longitude guess.
- Sampled against the authoritative `/metadata` `provinceCode`, that guess was **wrong
  ~50% of the time** — e.g. Digby shown as QC (actually NS), Sambro Harbour QC→NS,
  Blanc-Sablon NT→QC, many Nunavut stations shown as NT, Cape Tormentine QC→NB.

So roughly half of all Canadian stations displayed the wrong province.

**Why not fetch `/metadata` at startup:** the authoritative `provinceCode` lives only
in the per-station `/metadata` endpoint (the bulk `/stations` list omits it), and CHS
rate-limits hard enough that ~1,076 calls take 15+ min — infeasible at container start.

**Resolved:** Precompute the map offline and ship it.
- `scripts/fetch_canadian_provinces.py` (rate-limited, retrying, resumable) fetches
  `provinceCode` for every calendar-capable station and writes
  `app/canadian_station_provinces.csv` (`code,province`). Run it occasionally
  (alongside `validate_tide_stations.py`).
- `canadian_station_sync.PROVINCE_BY_CODE` loads that CSV once at import;
  `normalize_station()` resolves province as **map → name → longitude fallback**, and
  now also populates the `province` column (fixing the empty-column issue noted below).
  Longitude inference remains only as a graceful fallback for codes not yet in the map.
- The new CSV is added to the Dockerfile `COPY` lines so it ships in the image.

**Note (now resolved):** the `province` **column** used to be left empty for inferred
stations; with the map it is populated from the authoritative code.

---

## 2. Diacritic-insensitive search ✅ DONE

**Was:** Search was a plain `LOWER() LIKE` match, so the ASCII "kalpilin" did not
match the official "ḵalpilin" (U+1E35).

**Resolved:** Added `fold_for_search()` in `database.py` (NFKD decomposition + combining-
mark removal + lowercase) and registered it as a SQLite `fold()` function used by
`search_stations_by_country()` (the query is folded in Python, then matched with
`fold(place_name) LIKE ? OR fold(alternative_name) LIKE ?`). NFKD turned out to decompose
`ḵ`→`k` (plus combining macron) on its own,
so no custom character map was needed; the same fold also handles French accents
(`Bécancour`→`becancour`, `Île`→`ile`). Search-only change — no schema/import/backfill.
Covered by `TestFoldForSearch` and `TestDiacriticInsensitiveSearch`.

---

## 3. Messy CHS `alternativeName` values ✅ FIXED

**Was:** Many CHS alternate names are messy lists of echoes/variants — case echoes
(`Dumb Bell Bay, DUMB BELL BAY`), exact repeats (`Payne Bay, Payne Bay`), duplicated
multi-segment (`Parry Passage, B.C., Parry Passage, B.C.`), and genuine multi-name
lists (`Sugluk, Salluit, Saglouc`). 58 of 163 alternate names contain commas. These
rendered as ugly labels like `Dumb Bell Bay, DUMB BELL BAY (Alert), NT`.

**Resolved:** Rather than scrub the stored value, **decouple search from display** —
`format_display_name()` now leads with only the **first comma-segment** of the
alternate name (reliably the primary common name). The full value stays stored, so
**search still matches any variant** (verified: "saglouc", "broughton", "dumb bell" all
still resolve). No data, schema, or import change.

Result: `Dumb Bell Bay (Alert), NT`, `Broughton Island (Qikiqtarjuaq), NU`,
`Sugluk (Salluit), QC`, `Parry Passage (Henslung Cove), BC`. Covered by
`TestFormatDisplayName` and `TestMessyAlternativeNameSearchAndDisplay`.

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

## 5. Empty calendars from newly-surfaced stations ✅ INVESTIGATED + MITIGATED

**Problem:** Relaxing the import filter to "any station with `wlp-hilo`" added ~1,005
stations. Some are inactive and have only historical data, so they are selectable by
name but yield no calendar for a current/future month.

**Findings (audited against the live CHS API, June 2026):**
- Empty-for-current-month rate is **low single digits** — ~2.4% in a clean bounded
  sample, ~7% in an earlier partial run → roughly **25–75 of 1,076** stations.
- Every empty station is an obscure **non-operating, TEMPORARY** point (Tanquary Camp,
  Diana Bay, Port Leopold, Cape Liverpool, Baychimo…) — Arctic research/survey sites,
  not places typical visitors search for.
- **The originally-proposed mitigation — "verify prediction availability at import" — is
  infeasible.** CHS rate-limits aggressively: even ~1,076 sequential calls at 4/sec fail
  en masse, and a full check takes 40+ minutes. Running that at container startup would
  break deploys. (A one-off `~1,076`-request audit literally spent 39 min wall-clock /
  34s CPU stuck in retry-backoff before being killed.)

**Mitigation applied (this change):** The empty case already degrades gracefully —
`get_tides.py` writes no PDF, so `routes.py` returns the error template. Replaced the
generic "PDF file not found." / "PDF file is empty." text with a clear, station- and
period-specific message explaining the station may be inactive / historical-only and to
try another station or month (web form and `/api/generate_quick`). `error_detail`
logging (`pdf_missing` / `pdf_empty`) is unchanged for analytics.

**Optional remaining work:** A periodic *offline* maintenance script (rate-limited, run
occasionally — not at startup) could flag stations that are persistently empty and stamp
a DB column to drop them from autocomplete. Low priority given the small, obscure set.
Watching `/admin/analytics` for `pdf_empty`/`pdf_missing` upticks remains the cheapest
ongoing signal.

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
