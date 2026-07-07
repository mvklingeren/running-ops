"""hill_cost: hand-computed pace penalty from grade-adjusted speed."""
import unittest

import pandas as pd

from analysis.elevation import hill_cost


class TestHillCost(unittest.TestCase):
    def test_hand_computed(self):
        # actual pace 360 s/km; GAP speed 1000/350 m/s = 350 s/km flat
        # equivalent -> the hills cost 10 s/km
        df = pd.DataFrame({"pace_s": [360.0],
                           "avgGradeAdjustedSpeed": [1000 / 350]})
        self.assertAlmostEqual(hill_cost(df).iloc[0], 10.0)

    def test_downhill_is_negative(self):
        # GAP pace slower than actual = terrain helped -> negative cost
        df = pd.DataFrame({"pace_s": [340.0],
                           "avgGradeAdjustedSpeed": [1000 / 350]})
        self.assertAlmostEqual(hill_cost(df).iloc[0], -10.0)


if __name__ == "__main__":
    unittest.main()
