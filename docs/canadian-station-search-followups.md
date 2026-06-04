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

## 4. Stale CSV fallback (`app/canadian_tide_stations.csv`) ✅ FIXED

**Was:** The CSV fallback (used only when the CHS API is unreachable at startup) was a
stale 10-row hand-curated set with no `alternative_name` column — so an API outage
degraded the site to a fraction of its stations with no common-name search. It also
caused a pre-existing failure in `scripts/test_multi_country_offline.py` ("Get Canadian
station info (Halifax) — Wrong API source: None") because Halifax wasn't in it.

**Resolved:** Added `scripts/generate_canadian_fallback_csv.py`, which snapshots a full
live import to `app/canadian_tide_stations.csv` — now **1,076 stations** with correct
provinces (from the baked map), `alternative_name`, and formatted place names, matching
normal operation. It's fast (one bulk `/stations` call + the local province map, no
per-station calls). Regenerate it occasionally alongside `fetch_canadian_provinces.py`.

The `test_multi_country_offline.py` Halifax check now passes (31/0). (These `scripts/`
tests still aren't run by CI — see #6/#7.)

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

## 6. Harden `format_display_name()` province split ✅ FIXED

**Was:** When no explicit province was passed, `format_display_name()` split the trailing
`", …"` off `place_name` via `rpartition(', ')` and treated the tail as the province —
correct only because `construct_place_name()` always appends `", PROV"`. A future
place_name with a comma but no province suffix would have been mis-split.

**Resolved:** The `rpartition` fallback now strips the tail only when it is a
province/state-code shape (`len(tail) == 2 and tail.isalpha()`, e.g. `", BC"`).
Otherwise the name is kept whole. Humanized labels like "Greenland" always arrive via
the explicit `province` arg (the province column is reliably populated since #1), so
they never depend on the fallback. Covered by
`TestFormatDisplayName.test_does_not_split_non_province_tail`.

---

## 7. (Optional) Consolidate the two `import_canadian_stations_from_csv()` ✅ RESOLVED (keep separate)

**Decision: keep them separate.** They are intentionally different, not accidental
duplicates:

| | `database.py` (offline scripts) | `canadian_station_sync.py` (API fallback) |
|--|--|--|
| "skip if already populated" guard | yes | no |
| removes stations not in the CSV (sync) | yes | no |
| coordinate parsing | graceful (None on bad data) | `float()` (raises) |

Merging them would force reconciling those sync semantics and **change behavior for one
caller** for only marginal "clarity" gain. The original concern — a data inconsistency —
is already gone (both write `alternative_name`). Instead of a risky merge, the
`canadian_station_sync.py` docstring now explains the distinction and cross-references
the `database.py` importer. No code consolidation.

---

## Reference: relevant code

- Import + filter + normalization: `app/canadian_station_sync.py`
  (`normalize_station`, `fetch_canadian_stations_from_api`, `construct_place_name`)
- Search + display formatting: `app/database.py`
  (`search_stations_by_country`, `get_popular_stations_by_country`, `format_display_name`)
- Frontend rendering: `app/templates/index.html` (autocomplete dropdown + popular table)
- Tests: `app/test_canadian_station_sync.py`, `app/test_station_search.py`
