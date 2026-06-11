# 🇨🇦 Canadian Tide Station Integration - Project Roadmap

## Overview
This document tracks the multi-phase project to integrate Canadian Hydrographic Service (CHS) tide stations into the Tide Calendar application.

**Project Goal:** Enable users to generate tide calendars for both USA (NOAA) and Canadian (CHS) tide stations through a unified interface.

**Start Date:** November 15, 2025
**Estimated Duration:** 5-6 weeks
**Project Status:** 🟢 Phase 1 Complete

---

## Project Structure

### GitHub Issues
All phases are tracked as GitHub issues with the `canadian-integration` label:

- **[#45](https://github.com/matt-the-ogre/tide-calendar-site/issues/45)** - Project Overview (this roadmap)
- **[#40](https://github.com/matt-the-ogre/tide-calendar-site/issues/40)** - Phase 2: API Adapter Layer
- **[#41](https://github.com/matt-the-ogre/tide-calendar-site/issues/41)** - Phase 3: Integration
- **[#42](https://github.com/matt-the-ogre/tide-calendar-site/issues/42)** - Phase 4: UI Updates
- **[#43](https://github.com/matt-the-ogre/tide-calendar-site/issues/43)** - Phase 5: Testing & QA
- **[#44](https://github.com/matt-the-ogre/tide-calendar-site/issues/44)** - Phase 6: Documentation & Deployment

---

## Phase Summary

### ✅ Phase 1: Data Foundation (COMPLETE)
**Duration:** 1 day
**Completed:** November 15, 2025
**Branch:** `claude/canada-tide-stations-plan-01GJSYSBGMXJZ3A7HbQdoECe`

**Accomplishments:**
- ✅ Created and executed database migration script
- ✅ Added 5 new columns: `country`, `api_source`, `latitude`, `longitude`, `province`
- ✅ Imported 24 Canadian tide stations covering 7 provinces
- ✅ Created 4 new database functions for multi-country support
- ✅ All tests passing (import, search, retrieval)
- ✅ Documentation complete (`PHASE1_COMPLETE.md`)

**Database State:**
- 24 Canadian stations 🇨🇦
- 2,909 USA stations 🇺🇸
- **Total: 2,933 stations**

**Files Created:**
- `app/migrate_database.py` - Migration script (idempotent)
- `app/canadian_tide_stations.csv` - Station data
- `app/test_canadian_import.py` - Test suite
- `PHASE1_COMPLETE.md` - Detailed documentation

**Files Modified:**
- `app/database.py` - Added 4 new functions (+193 lines)

---

### 🔲 Phase 2: API Adapter Layer
**Issue:** [#40](https://github.com/matt-the-ogre/tide-calendar-site/issues/40)
**Duration:** 1 week
**Status:** Not Started

**Goals:**
- Create abstract API adapter base class
- Implement NOAA adapter (refactor existing code)
- Implement CHS adapter for Canadian data
- Unified CSV response format
- Unit tests for all adapters

**Key Deliverables:**
- `app/tide_api_adapter.py` with `NOAATideAPI` and `CHSTideAPI` classes
- `tests/test_tide_api_adapters.py` with comprehensive test coverage
- Documentation of adapter interface

**Technical Details:**
- CHS API Base URL: `https://api-iwls.dfo-mpo.gc.ca/api/v1`
- Time series code: `wlp-hilo` (high/low predictions)
- Response format: JSON → CSV conversion
- Date format: ISO 8601 for CHS, YYYYMMDD for NOAA

---

### 🔲 Phase 3: Integration
**Issue:** [#41](https://github.com/matt-the-ogre/tide-calendar-site/issues/41)
**Duration:** 1 week
**Status:** Not Started
**Depends On:** Phase 2

**Goals:**
- Integrate API adapters into `get_tides.py`
- Automatic API selection based on station metadata
- Maintain backward compatibility with NOAA
- Test PDF generation with Canadian stations

**Key Deliverables:**
- Modified `app/get_tides.py` with adapter integration
- Modified `app/routes.py` with station info lookup
- Working PDF generation for both USA and Canadian stations

**Test Stations:**
- USA: 9449639 (Point Roberts, WA), 9410170 (San Diego, CA)
- Canada: 07735 (Vancouver, BC), 08615 (Tofino, BC), 00490 (Halifax, NS)

---

### 🔲 Phase 4: UI Updates
**Issue:** [#42](https://github.com/matt-the-ogre/tide-calendar-site/issues/42)
**Duration:** 1 week
**Status:** Not Started
**Depends On:** Phase 3

**Goals:**
- Add country selector to search interface
- Show country flags/indicators in search results
- Update popular stations for dual-country display
- Enhance form validation for different station ID formats

**Key Deliverables:**
- Modified `app/templates/index.html` with country selector
- Updated autocomplete with country indicators (🇺🇸 🇨🇦)
- Enhanced `app/routes.py` API endpoints with country filtering
- Responsive design for mobile/desktop

**UI Features:**
- Country filter: "All Countries", "USA", "Canada"
- Visual indicators: Flags or badges in autocomplete
- Grouped popular stations by country
- Clear error messages per country

---

### 🔲 Phase 5: Testing & QA
**Issue:** [#43](https://github.com/matt-the-ogre/tide-calendar-site/issues/43)
**Duration:** 1 week
**Status:** Not Started
**Depends On:** Phase 4

**Goals:**
- Comprehensive functional testing with 10+ Canadian stations
- Regression testing for USA stations
- Performance benchmarking
- Cross-browser and mobile testing
- Accessibility audit

**Test Coverage:**
- Functional: 10+ Canadian stations, 5+ USA stations
- Edge cases: Invalid IDs, API errors, leap years, etc.
- Performance: <3s PDF generation, <500ms search response
- Browsers: Chrome, Firefox, Safari, Edge, Mobile
- Accessibility: WCAG 2.1 AA compliance

**Success Metrics:**
- Zero regressions in USA functionality
- All Canadian stations generate valid PDFs
- Performance targets met
- Cross-browser compatibility confirmed

---

### 🔲 Phase 6: Documentation & Deployment
**Issue:** [#44](https://github.com/matt-the-ogre/tide-calendar-site/issues/44)
**Duration:** 1 week
**Status:** Not Started
**Depends On:** Phase 5

**Goals:**
- Update all documentation (README, CLAUDE.md)
- Production deployment to CapRover
- Monitoring and analytics setup
- User communication and announcement

**Key Deliverables:**
- Updated README.md with Canadian station support
- Updated CLAUDE.md with architecture details
- User guide for finding station IDs
- Production deployment runbook
- Monitoring dashboard
- Release announcement

**Deployment:**
- Merge to `main` branch
- GitHub webhook triggers CapRover auto-deployment
- Database migration runs on startup
- Zero-downtime deployment
- Post-deployment monitoring for 24 hours

---

## Technical Architecture

### API Adapter Pattern
```
User Request
    ↓
routes.py (get station info from DB)
    ↓
get_tides.py (select adapter based on api_source)
    ↓
┌─────────────────┐
│ TideAPIAdapter  │ (abstract base class)
└────────┬────────┘
         │
    ┌────┴────┐
    ↓         ↓
NOAATideAPI  CHSTideAPI
    │            │
    ↓            ↓
NOAA API    CHS IWLS API
    │            │
    └────┬───────┘
         ↓
   CSV Format (unified)
         ↓
   pcal conversion
         ↓
   PDF Calendar
```

### Database Schema (Enhanced)
```sql
CREATE TABLE tide_station_ids (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    station_id TEXT UNIQUE NOT NULL,
    place_name TEXT,
    country TEXT NOT NULL DEFAULT 'USA',       -- NEW
    api_source TEXT NOT NULL DEFAULT 'NOAA',   -- NEW
    latitude REAL,                              -- NEW
    longitude REAL,                             -- NEW
    province TEXT,                              -- NEW
    lookup_count INTEGER NOT NULL DEFAULT 1,
    last_lookup DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

---

## Key Statistics

### Current Database
- **Canadian Stations:** 24
- **USA Stations:** 2,909
- **Total Stations:** 2,933

### Canadian Station Coverage
- British Columbia (BC): 10 stations
- Quebec (QC): 4 stations
- Nova Scotia (NS): 3 stations
- Newfoundland and Labrador (NL): 3 stations
- New Brunswick (NB): 1 station
- Prince Edward Island (PE): 1 station
- Northwest Territories (NT): 1 station
- Other: 1 station

### Example Stations
| Country | Station ID | Location | Coordinates |
|---------|------------|----------|-------------|
| 🇨🇦 | 07735 | Vancouver, BC | 49.334, -123.266 |
| 🇨🇦 | 08615 | Tofino, BC | 49.153, -125.913 |
| 🇨🇦 | 00490 | Halifax, NS | 44.667, -63.583 |
| 🇺🇸 | 9449639 | Point Roberts, WA | 48.984, -123.080 |
| 🇺🇸 | 9410170 | San Diego, CA | 32.714, -117.173 |

---

## API References

### NOAA Tides & Currents API
- **Base URL:** `https://api.tidesandcurrents.noaa.gov/api/prod/datagetter`
- **Station Format:** 7-digit numeric (e.g., `9449639`)
- **Date Format:** `YYYYMMDD`
- **Response:** CSV
- **Documentation:** https://tidesandcurrents.noaa.gov/web_services_info.html

### Canadian Hydrographic Service IWLS API
- **Base URL:** `https://api-iwls.dfo-mpo.gc.ca/api/v1`
- **Station Format:** 5-digit numeric (e.g., `07735`)
- **Date Format:** ISO 8601 (`YYYY-MM-DDTHH:MM:SSZ`)
- **Response:** JSON
- **Documentation:** https://api-iwls.dfo-mpo.gc.ca/swagger-ui/index.html
- **Station Lookup:** https://tides.gc.ca/en/stations

---

## Timeline

| Phase | Duration | Status | Start Date | End Date |
|-------|----------|--------|------------|----------|
| Phase 1 | 1 day | ✅ Complete | Nov 15, 2025 | Nov 15, 2025 |
| Phase 2 | 1 week | 🔲 Not Started | TBD | TBD |
| Phase 3 | 1 week | 🔲 Not Started | TBD | TBD |
| Phase 4 | 1 week | 🔲 Not Started | TBD | TBD |
| Phase 5 | 1 week | 🔲 Not Started | TBD | TBD |
| Phase 6 | 1 week | 🔲 Not Started | TBD | TBD |
| **Total** | **5-6 weeks** | **16% Complete** | **Nov 15, 2025** | **~Early 2026** |

---

## Risk Assessment

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| CHS API changes/deprecation | High | Low | Monitor API announcements, version detection |
| API rate limiting | Medium | Medium | Implement caching, respect rate limits |
| Different data quality | Medium | Low | Validation, show data source on PDF |
| Station ID confusion | Low | Medium | Clear UI labeling, validation |
| Database migration issues | Low | Low | Thorough testing, backup before deploy |

---

## Success Criteria

### Overall Project Success
- [ ] Users can generate PDFs for both USA and Canadian stations
- [ ] UI clearly distinguishes between countries
- [ ] No regressions in existing USA functionality
- [ ] Performance meets or exceeds current standards
- [ ] Documentation is comprehensive
- [ ] Production deployment successful with zero downtime

### Phase-Specific Criteria
See individual phase issues for detailed success criteria.

---

## Project Resources

### Documentation
- [PHASE1_COMPLETE.md](./PHASE1_COMPLETE.md) - Phase 1 detailed summary
- [CLAUDE.md](./CLAUDE.md) - Project instructions for Claude Code
- [README.md](./README.md) - Main project README

### GitHub
- [Project Issues](https://github.com/matt-the-ogre/tide-calendar-site/issues?q=label%3Acanadian-integration)
- [Phase 1 Branch](https://github.com/matt-the-ogre/tide-calendar-site/tree/claude/canada-tide-stations-plan-01GJSYSBGMXJZ3A7HbQdoECe)

### External APIs
- [NOAA API Docs](https://tidesandcurrents.noaa.gov/web_services_info.html)
- [CHS IWLS API](https://api-iwls.dfo-mpo.gc.ca/swagger-ui/index.html)
- [CHS Station Search](https://tides.gc.ca/en/stations)

---

## Contact

**Project Lead:** @matt-the-ogre
**Questions:** Create an issue with the `canadian-integration` label

---

*Last Updated: November 15, 2025*
