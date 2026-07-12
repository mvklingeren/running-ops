"""Banister TRIMP, normalized power / PSS, and TSB projection against
hand-computed and closed-form values."""
import math
import unittest

import pandas as pd

from analysis.load import np_power, pmc, project_tsb, pss, trimp

HR_REST, HR_MAX = 40.0, 200.0


class TestTrimp(unittest.TestCase):
    def test_hand_computed_constant_hr(self):
        # HR 120 -> HRR = 0.5 for one hour:
        # TRIMP = 60 min * 0.5 * 0.64 * e^(1.92*0.5) = 50.145
        hr = pd.Series([120.0] * 3600)
        expected = 60 * 0.5 * 0.64 * math.exp(0.96)
        self.assertAlmostEqual(trimp(hr, HR_REST, HR_MAX), expected, places=6)

    def test_below_rest_clipped_to_zero(self):
        hr = pd.Series([35.0] * 600)  # under resting HR -> no load
        self.assertEqual(trimp(hr, HR_REST, HR_MAX), 0.0)

    def test_higher_intensity_weighs_exponentially(self):
        # 30 min at HRR 0.9 must far outweigh 60 min at HRR 0.45
        hard = trimp(pd.Series([184.0] * 1800), HR_REST, HR_MAX)
        easy = trimp(pd.Series([112.0] * 3600), HR_REST, HR_MAX)
        self.assertGreater(hard, easy * 1.5)


class TestPss(unittest.TestCase):
    def test_np_of_constant_power_is_that_power(self):
        self.assertAlmostEqual(np_power(pd.Series([250.0] * 600)), 250.0,
                               places=6)

    def test_one_hour_at_cp_scores_100(self):
        self.assertAlmostEqual(pss(pd.Series([300.0] * 3600), 300.0), 100.0,
                               places=6)

    def test_np_weighs_surges_above_average(self):
        # 30 min at 200 W + 30 min at 400 W: NP must exceed the 300 W mean
        p = pd.Series([200.0] * 1800 + [400.0] * 1800)
        self.assertGreater(np_power(p), 300.0)

    def test_no_power_is_nan(self):
        self.assertTrue(math.isnan(pss(pd.Series([float("nan")] * 60), 300.0)))


class TestProjectTsb(unittest.TestCase):
    def test_steady_load_converges_to_zero_tsb(self):
        # constant load forever: ATL = CTL, so TSB -> 0
        idx = pd.date_range("2026-01-01", periods=200, freq="D")
        daily = pd.Series(50.0, index=idx)
        t = project_tsb(daily, idx[-1] + pd.Timedelta(days=60), factor=1.0)
        self.assertAlmostEqual(t, 0.0, delta=0.5)

    def test_rest_raises_tsb(self):
        idx = pd.date_range("2026-01-01", periods=200, freq="D")
        daily = pd.Series(50.0, index=idx)
        race = idx[-1] + pd.Timedelta(days=14)
        self.assertGreater(project_tsb(daily, race, factor=0.0),
                           pmc(daily)[2].iloc[-1] + 5)


if __name__ == "__main__":
    unittest.main()
