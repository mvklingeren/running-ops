"""Banister TRIMP against the hand-computed value."""
import math
import unittest

import pandas as pd

from analysis.load import trimp

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


if __name__ == "__main__":
    unittest.main()
