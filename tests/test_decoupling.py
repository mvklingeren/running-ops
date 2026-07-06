"""Aerobic decoupling on a synthetic run with a known HR step."""
import unittest

import pandas as pd

from analysis.decoupling import WARMUP, decoupling


def stream(power, hr):
    return pd.DataFrame({"power": power, "hr": hr})


class TestDecoupling(unittest.TestCase):
    def test_exact_drift_from_hr_step(self):
        # constant power; HR 150 through warmup + first half, 160 second half
        n = 2000
        half = WARMUP + (n - WARMUP) // 2  # 1150
        s = stream([300.0] * n, [150.0] * half + [160.0] * (n - half))
        # EF1 = 300/150 = 2.0, EF2 = 300/160 -> drift = 1 - 150/160
        self.assertAlmostEqual(decoupling(s), 1 - 150 / 160, places=6)

    def test_no_drift_when_steady(self):
        s = stream([300.0] * 2000, [150.0] * 2000)
        self.assertAlmostEqual(decoupling(s), 0.0, places=9)

    def test_short_run_skipped(self):
        s = stream([300.0] * 600, [150.0] * 600)
        self.assertIsNone(decoupling(s))


if __name__ == "__main__":
    unittest.main()
