"""time_in_zones must bucket %CP samples correctly, lower bound inclusive."""
import unittest

import pandas as pd

from analysis.zones import ZONES, time_in_zones

CP = 300.0


class TestTimeInZones(unittest.TestCase):
    def test_one_sample_per_zone(self):
        # 0.5, 0.85, 0.95, 1.05, 1.2 x CP -> exactly one second in each zone
        power = pd.Series([f * CP for f in (0.5, 0.85, 0.95, 1.05, 1.2)])
        self.assertEqual(time_in_zones(power, CP), [1, 1, 1, 1, 1])

    def test_boundary_belongs_to_upper_zone(self):
        # exactly 80% of CP is Z2, just below is Z1
        power = pd.Series([0.80 * CP, 0.80 * CP - 0.1])
        self.assertEqual(time_in_zones(power, CP)[:2], [1, 1])

    def test_totals_preserved(self):
        power = pd.Series(range(0, 600))
        self.assertEqual(sum(time_in_zones(power, CP)), len(power))
        self.assertEqual(len(time_in_zones(power, CP)), len(ZONES))


if __name__ == "__main__":
    unittest.main()
