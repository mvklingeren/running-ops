"""Interval discovery on a synthetic square-wave power signal."""
import unittest

import pandas as pd

from analysis.intervals import find_intervals

CP = 300.0
TOL = 35  # 30 s smoothing blurs edges by up to ~half a window + change


def square_wave():
    """2000 s: two efforts above CP, a short dip inside the first,
    and a 40 s spike that is too short to count."""
    p = [200.0] * 2000
    p[600:900] = [400.0] * 300     # effort A (300 s)
    p[700:725] = [200.0] * 25      # 25 s dip inside A -> must be merged
    p[1200:1401] = [400.0] * 201   # effort B (201 s)
    p[1600:1640] = [400.0] * 40    # too short -> must be dropped
    return pd.Series(p)


class TestFindIntervals(unittest.TestCase):
    def test_detection_merge_and_min_length(self):
        found = find_intervals(square_wave(), CP)
        self.assertEqual(len(found), 2)

        (s1, e1), (s2, e2) = found
        # effort A: detected near its true bounds, dip did not split it
        self.assertAlmostEqual(s1, 600, delta=TOL)
        self.assertAlmostEqual(e1, 900, delta=TOL)
        self.assertLess(s1, 700)
        self.assertGreater(e1, 725)
        # effort B
        self.assertAlmostEqual(s2, 1200, delta=TOL)
        self.assertAlmostEqual(e2, 1400, delta=TOL)

    def test_steady_run_has_no_intervals(self):
        self.assertEqual(find_intervals(pd.Series([250.0] * 1200), CP), [])


if __name__ == "__main__":
    unittest.main()
