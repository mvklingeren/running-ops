"""Daniels/Gilbert model against published VDOT race tables."""
import unittest

import pandas as pd

from analysis.vo2max import (effective_vo2max, fmt_time, pct_at_duration,
                             predict, vo2_cost)


class TestDanielsTables(unittest.TestCase):
    """Published VDOT tables (Daniels' Running Formula)."""

    def assert_close(self, minutes, mm_ss, tol=0.015):
        m, s = mm_ss.split(":")[-2:]
        expected = (int(mm_ss.split(":")[0]) * 60 if mm_ss.count(":") == 2
                    else 0) + int(m) + int(s) / 60
        self.assertAlmostEqual(minutes, expected, delta=expected * tol)

    def test_vdot_50(self):
        self.assert_close(predict(50, 5000), "19:57")
        self.assert_close(predict(50, 10000), "41:21")
        self.assert_close(predict(50, 42195), "3:10:49")

    def test_vdot_60(self):
        self.assert_close(predict(60, 5000), "17:03")


class TestModelProperties(unittest.TestCase):
    def test_vo2max_sustainable_about_11_minutes(self):
        self.assertAlmostEqual(pct_at_duration(11), 1.0, delta=0.01)

    def test_oxygen_cost_spot_value(self):
        # Daniels/Gilbert: ~51.7 ml/kg/min at 268 m/min
        self.assertAlmostEqual(vo2_cost(268), 51.7, delta=0.1)

    def test_effective_vo2max_round_trip(self):
        # 200 m/min at HR = HRmax: %VO2max = (1-0.37)/0.64
        runs = pd.DataFrame({"distance": [3000.0], "duration": [900.0],
                             "averageHR": [190.0]})
        expected = vo2_cost(200) / ((1 - 0.37) / 0.64)
        self.assertAlmostEqual(effective_vo2max(runs, 190).iloc[0], expected,
                               places=6)


class TestFmtTime(unittest.TestCase):
    def test_with_hours(self):
        self.assertEqual(fmt_time(190 + 49 / 60), "3:10:49")

    def test_without_hours(self):
        self.assertEqual(fmt_time(19.95), "19:57")


if __name__ == "__main__":
    unittest.main()
