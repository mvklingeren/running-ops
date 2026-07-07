"""quadrant_split: four corner points land in four distinct quadrants."""
import unittest

import pandas as pd

from analysis.quadrant import quadrant_split


class TestQuadrantSplit(unittest.TestCase):
    def test_corner_points(self):
        # medians are 2 (force) and 170 (cadence); >= goes to the hi side
        df = pd.DataFrame({"force": [3.0, 3.0, 1.0, 1.0],
                           "cadence": [160.0, 180.0, 180.0, 160.0]})
        f_med, c_med, quads = quadrant_split(df)
        self.assertEqual(f_med, 2.0)
        self.assertEqual(c_med, 170.0)
        # order is Q1 grind, Q2 power, Q3 spin, Q4 easy — one point each,
        # matching the row order above
        for i, (name, mask) in enumerate(quads):
            self.assertEqual(mask.sum(), 1, name)
            self.assertTrue(mask.iloc[i], name)

    def test_median_point_is_hi_side(self):
        df = pd.DataFrame({"force": [2.0, 2.0, 2.0],
                           "cadence": [170.0, 170.0, 170.0]})
        _, _, quads = quadrant_split(df)
        self.assertEqual(quads[1][1].sum(), 3)  # all in Q2 power


if __name__ == "__main__":
    unittest.main()
