import unittest
import units


class UnitsTest(unittest.TestCase):
    def test_metric_passthrough(self):
        self.assertEqual(units.convert(3.0, 'metric'), 3.0)

    def test_imperial_feet(self):
        self.assertEqual(units.convert(1.0, 'imperial'), 3.3)   # 3.28084 -> 3.3
        self.assertEqual(units.convert(-1.2, 'imperial'), -3.9)

    def test_suffix(self):
        self.assertEqual(units.suffix('metric'), 'm')
        self.assertEqual(units.suffix('imperial'), 'ft')

    def test_unknown_unit_defaults_metric(self):
        self.assertEqual(units.convert(2.0, 'bogus'), 2.0)
        self.assertEqual(units.suffix('bogus'), 'm')


if __name__ == '__main__':
    unittest.main()
