"""W'bal (Skiba differential) against closed-form solutions."""
import math
import unittest

import pandas as pd

from analysis.wbal import wbal_series

CP, W_PRIME = 300.0, 20_000.0


class TestWbal(unittest.TestCase):
    def test_linear_drain_above_cp(self):
        # constant 350 W: tank drains at exactly 50 J/s
        power = pd.Series([350.0] * 100)
        wb = wbal_series(power, CP, W_PRIME)
        self.assertAlmostEqual(wb.iloc[-1], W_PRIME - 50 * 100)
        self.assertAlmostEqual(wb.iloc[0], W_PRIME - 50)

    def test_recovery_matches_closed_form(self):
        # drain 5 kJ, then recover at 250 W (50 W below CP).
        # Continuous model: deficit(t) = D * exp(-(CP-P)*t / W')
        power = pd.Series([350.0] * 100 + [250.0] * 400)
        wb = wbal_series(power, CP, W_PRIME)
        deficit = 5000 * math.exp(-50 * 400 / W_PRIME)
        self.assertAlmostEqual(wb.iloc[-1], W_PRIME - deficit, delta=25)

    def test_never_exceeds_w_prime(self):
        power = pd.Series([0.0] * 500)  # standing still
        wb = wbal_series(power, CP, W_PRIME)
        self.assertTrue((wb <= W_PRIME).all())
        self.assertAlmostEqual(wb.iloc[-1], W_PRIME, delta=1)


if __name__ == "__main__":
    unittest.main()
