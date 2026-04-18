#!/usr/bin/env python3
"""
Tests for usage_events analytics: schema, insert helper, stats aggregation,
retention pruning, and source tagging.

Run: python3 scripts/test_usage_events.py
Exits 0 on success, 1 on any assertion failure.
"""

import os
import sys
import sqlite3
import tempfile
from pathlib import Path

APP_DIR = Path(__file__).parent.parent / 'app'
sys.path.insert(0, str(APP_DIR))


def _fresh_db():
    """Create a throwaway DB and re-import the database module against it."""
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    os.environ['DB_PATH'] = path
    # Force reimport so DB_PATH is re-read at module level
    if 'database' in sys.modules:
        del sys.modules['database']
    import database
    database.init_database()
    return database, path


def test_schema_and_index_exist():
    print("\n=== test_schema_and_index_exist ===")
    db, path = _fresh_db()
    try:
        with sqlite3.connect(path) as conn:
            cols = [row[1] for row in conn.execute("PRAGMA table_info(usage_events)")]
            expected = {'id', 'timestamp', 'station_id', 'station_name', 'year', 'month', 'status', 'error_detail', 'source'}
            missing = expected - set(cols)
            assert not missing, f"Missing columns: {missing}"

            indexes = [row[1] for row in conn.execute("PRAGMA index_list(usage_events)")]
            assert 'idx_usage_events_timestamp' in indexes, f"Missing index. Got: {indexes}"
        print("  PASS: table has all expected columns + timestamp index")
    finally:
        os.remove(path)


def test_log_usage_event_success_and_error():
    print("\n=== test_log_usage_event_success_and_error ===")
    db, path = _fresh_db()
    try:
        db.log_usage_event('9449639', 'Point Roberts, WA', 2026, 5, 'success')
        db.log_usage_event(None, None, None, None, 'error', 'invalid_input')
        db.log_usage_event('1234567', None, 2026, 5, 'error', 'pdf_missing', source='quick_api')

        with sqlite3.connect(path) as conn:
            rows = conn.execute(
                'SELECT station_id, station_name, status, error_detail, source FROM usage_events ORDER BY id'
            ).fetchall()
            assert rows[0] == ('9449639', 'Point Roberts, WA', 'success', None, 'web'), rows[0]
            assert rows[1] == (None, None, 'error', 'invalid_input', 'web'), rows[1]
            assert rows[2] == ('1234567', None, 'error', 'pdf_missing', 'quick_api'), rows[2]
        print(f"  PASS: all 3 events persisted with correct fields and default source='web'")
    finally:
        os.remove(path)


def test_log_usage_event_swallows_db_errors():
    print("\n=== test_log_usage_event_swallows_db_errors ===")
    db, path = _fresh_db()
    try:
        # Point DB_PATH at a directory — sqlite will fail to connect
        bad_path = tempfile.mkdtemp()
        os.environ['DB_PATH'] = bad_path
        if 'database' in sys.modules:
            del sys.modules['database']
        import database as bad_db

        # Must not raise — failures are swallowed
        bad_db.log_usage_event('x', 'y', 2026, 5, 'success')
        print("  PASS: log_usage_event swallowed DB error without raising")

        os.rmdir(bad_path)
    finally:
        os.environ['DB_PATH'] = path
        if 'database' in sys.modules:
            del sys.modules['database']
        os.remove(path)


def test_get_usage_stats_aggregates():
    print("\n=== test_get_usage_stats_aggregates ===")
    db, path = _fresh_db()
    try:
        db.log_usage_event('A', 'Station A', 2026, 1, 'success')
        db.log_usage_event('A', 'Station A', 2026, 2, 'success')
        db.log_usage_event('B', 'Station B', 2026, 1, 'success', source='quick_api')
        db.log_usage_event(None, None, None, None, 'error', 'invalid_input')
        db.log_usage_event('C', None, 2026, 1, 'error', 'pdf_missing')

        stats = db.get_usage_stats()
        assert stats['total'] == 5, stats
        assert stats['success_count'] == 3, stats
        assert stats['error_count'] == 2, stats
        assert stats['web_count'] == 4, stats
        assert stats['quick_api_count'] == 1, stats
        assert stats['last_24h'] == 5, stats  # all just inserted
        assert 'error' not in stats, "No DB error expected on happy path"

        # Top stations: only named stations within 30d, in hit-count order
        top = stats['top_stations']
        top_names = [s['station_name'] for s in top]
        assert 'Station A' in top_names, top_names
        assert top[0]['hits'] == 2, top  # Station A (2 hits) > Station B (1 hit)
        # Error event with station_id='C' but no name is filtered out
        assert 'C' not in top_names
        assert None not in top_names

        # Recent events include all 5, newest first, with source tag
        assert len(stats['recent_events']) == 5
        assert stats['recent_events'][0]['status'] in ('success', 'error')
        assert 'source' in stats['recent_events'][0]
        print("  PASS: totals, source breakdown, top_stations, and recent_events all correct")
    finally:
        os.remove(path)


def test_retention_prunes_old_events():
    print("\n=== test_retention_prunes_old_events ===")
    db, path = _fresh_db()
    try:
        # Manually insert an event backdated beyond the retention window
        with sqlite3.connect(path) as conn:
            conn.execute("""
                INSERT INTO usage_events (timestamp, station_id, station_name, status, source)
                VALUES (datetime('now', '-400 days'), 'OLD', 'Old Station', 'success', 'web')
            """)
            conn.execute("""
                INSERT INTO usage_events (timestamp, station_id, station_name, status, source)
                VALUES (datetime('now', '-10 days'), 'NEW', 'New Station', 'success', 'web')
            """)
            conn.commit()
            before = conn.execute('SELECT COUNT(*) FROM usage_events').fetchone()[0]
            assert before == 2, before

        # Re-initialize — prune runs in init_database
        db.init_database()

        with sqlite3.connect(path) as conn:
            remaining = conn.execute(
                'SELECT station_id FROM usage_events ORDER BY id'
            ).fetchall()
            assert len(remaining) == 1, remaining
            assert remaining[0][0] == 'NEW', remaining
        print("  PASS: events older than 365 days pruned on init; recent events preserved")
    finally:
        os.remove(path)


def test_get_usage_stats_error_path():
    print("\n=== test_get_usage_stats_error_path ===")
    # Point to a path where we can't open a db (a directory)
    bad_path = tempfile.mkdtemp()
    os.environ['DB_PATH'] = bad_path
    if 'database' in sys.modules:
        del sys.modules['database']
    import database as bad_db

    try:
        stats = bad_db.get_usage_stats()
        assert stats['total'] == 0
        assert stats['success_count'] == 0
        assert 'error' in stats, f"Expected 'error' key in sentinel dict; got {list(stats.keys())}"
        assert stats['top_stations'] == []
        assert stats['recent_events'] == []
        print("  PASS: get_usage_stats returns sentinel dict with 'error' key on DB failure")
    finally:
        os.rmdir(bad_path)
        if 'database' in sys.modules:
            del sys.modules['database']


def main():
    tests = [
        test_schema_and_index_exist,
        test_log_usage_event_success_and_error,
        test_log_usage_event_swallows_db_errors,
        test_get_usage_stats_aggregates,
        test_retention_prunes_old_events,
        test_get_usage_stats_error_path,
    ]
    failed = []
    for t in tests:
        try:
            t()
        except AssertionError as e:
            print(f"  FAIL: {t.__name__}: {e}")
            failed.append(t.__name__)
        except Exception as e:
            print(f"  ERROR: {t.__name__}: {type(e).__name__}: {e}")
            failed.append(t.__name__)

    print(f"\n{'=' * 50}")
    if failed:
        print(f"FAILED: {len(failed)}/{len(tests)} tests")
        for name in failed:
            print(f"  - {name}")
        sys.exit(1)
    print(f"PASSED: all {len(tests)} tests")


if __name__ == '__main__':
    main()
