"""ef_by_kj and fade against streams with known closed-form answers."""
import unittest

import pandas as pd

from analysis.durability import BIN_KJ, ef_by_kj, fade


def stream(power, hr, n=4000):
    return pd.DataFrame({"power": power, "hr": hr}, index=range(n))


class TestEfByKj(unittest.TestCase):
    def test_constant_ef_is_flat(self):
        # 250 W for 4000 s = 1000 kJ -> bins 0..10, all exactly 1.0
        c = ef_by_kj(stream(250.0, 150.0))
        self.assertEqual(c.index[0], 0)
        self.assertEqual(c.index[-1], 10)
        self.assertAlmostEqual(float((c - 1.0).abs().max()), 0.0, places=12)

    def test_step_drop_in_ef(self):
        # HR doubles halfway (t=2000 s = 500 kJ at 250 W): EF halves
        hr = [125.0] * 2000 + [250.0] * 2000
        c = ef_by_kj(stream(250.0, hr))
        self.assertEqual(c[3], 1.0)   # before the step
        self.assertEqual(c[7], 0.5)   # after the step

    def test_short_stream_returns_none(self):
        self.assertIsNone(ef_by_kj(stream(250.0, 150.0, n=100)))  # < warmup


class TestFade(unittest.TestCase):
    def test_recovers_exact_slope(self):
        # rel EF = 1 - 0.01 per bin at centers (i+.5)*BIN_KJ
        c = pd.Series([1 - 0.01 * i for i in range(10)], index=range(10))
        slope, intercept = fade([(None, c)])
        self.assertAlmostEqual(slope, -0.01 / BIN_KJ, places=12)
        self.assertAlmostEqual(intercept + slope * BIN_KJ / 2, 1.0, places=12)


if __name__ == "__main__":
    unittest.main()
