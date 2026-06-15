import os, tempfile, unittest, csv
os.environ.setdefault('DB_PATH', os.path.join(tempfile.gettempdir(), 'test_station_map.db'))

import database


class ImportCoordsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.tmp.close()
        database.DB_PATH = self.tmp.name
        database.init_database()

    def tearDown(self):
        os.unlink(self.tmp.name)

    def _seed_csv(self, monkeypatch_rows):
        path = self.tmp.name + '.csv'
        with open(path, 'w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=['station_id', 'place_name', 'latitude', 'longitude'])
            w.writeheader()
            w.writerows(monkeypatch_rows)
        return path

    def test_import_persists_coordinates(self):
        import sqlite3
        rows = [{'station_id': '9449639', 'place_name': 'Point Roberts, WA',
                 'latitude': '48.97', 'longitude': '-123.07'}]
        csv_path = self._seed_csv(rows)
        database._import_us_csv(csv_path)
        with sqlite3.connect(database.DB_PATH) as conn:
            lat, lng = conn.execute(
                'SELECT latitude, longitude FROM tide_station_ids WHERE station_id=?',
                ('9449639',)).fetchone()
        self.assertAlmostEqual(lat, 48.97)
        self.assertAlmostEqual(lng, -123.07)


class StationsWithCoordsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.tmp.close()
        database.DB_PATH = self.tmp.name
        database.init_database()
        import sqlite3
        with sqlite3.connect(database.DB_PATH) as conn:
            conn.execute("INSERT INTO tide_station_ids (station_id, place_name, country, latitude, longitude) "
                         "VALUES ('111','Has Coords','USA',47.6,-122.3)")
            conn.execute("INSERT INTO tide_station_ids (station_id, place_name, country) "
                         "VALUES ('222','No Coords','USA')")
            conn.commit()

    def tearDown(self):
        os.unlink(self.tmp.name)

    def test_excludes_null_coords(self):
        rows = database.get_stations_with_coordinates()
        ids = {r['station_id'] for r in rows}
        self.assertIn('111', ids)
        self.assertNotIn('222', ids)
        r = next(r for r in rows if r['station_id'] == '111')
        self.assertEqual(r['latitude'], 47.6)
        self.assertEqual(r['longitude'], -122.3)
        self.assertEqual(r['country'], 'USA')
        self.assertEqual(r['name'], 'Has Coords')


class BackfillTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.tmp.close()
        database.DB_PATH = self.tmp.name
        database.init_database()
        import sqlite3
        with sqlite3.connect(database.DB_PATH) as conn:
            conn.execute("INSERT INTO tide_station_ids (station_id, place_name, country) "
                         "VALUES ('9449639','Point Roberts, WA','USA')")
            conn.commit()

    def tearDown(self):
        os.unlink(self.tmp.name)

    def test_backfills_missing(self):
        import station_coordinates
        calls = []
        def fake_fetch(url=None):
            calls.append(url)
            return {'9449639': {'lat': 48.97, 'lng': -123.07}}
        n = station_coordinates.backfill_missing_coordinates(fetcher=fake_fetch)
        self.assertEqual(n, 1)
        self.assertEqual(len(calls), 1)
        info = database.get_station_info('9449639')
        self.assertAlmostEqual(info['latitude'], 48.97)

    def test_no_call_when_nothing_missing(self):
        import sqlite3, station_coordinates
        with sqlite3.connect(database.DB_PATH) as conn:
            conn.execute("UPDATE tide_station_ids SET latitude=1.0, longitude=2.0")
            conn.commit()
        calls = []
        station_coordinates.backfill_missing_coordinates(fetcher=lambda url=None: calls.append(url) or {})
        self.assertEqual(calls, [])


class StationsToGeojsonTest(unittest.TestCase):
    def test_builds_feature_collection(self):
        stations = [{'station_id': '9449639', 'name': 'Point Roberts, WA',
                     'country': 'USA', 'latitude': 48.97, 'longitude': -123.07}]
        geo = database.stations_to_geojson(stations)
        self.assertEqual(geo['type'], 'FeatureCollection')
        self.assertEqual(len(geo['features']), 1)
        f = geo['features'][0]
        self.assertEqual(f['type'], 'Feature')
        self.assertEqual(f['geometry']['type'], 'Point')
        self.assertEqual(f['geometry']['coordinates'], [-123.07, 48.97])
        self.assertEqual(f['properties']['station_id'], '9449639')
        self.assertEqual(f['properties']['name'], 'Point Roberts, WA')
        self.assertEqual(f['properties']['country'], 'USA')

    def test_empty(self):
        self.assertEqual(database.stations_to_geojson([]),
                         {'type': 'FeatureCollection', 'features': []})


if __name__ == '__main__':
    unittest.main()
