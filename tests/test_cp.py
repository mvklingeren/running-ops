"""fit_cp must exactly recover CP/W' from a synthetic hyperbolic MMP curve."""
import unittest

import pandas as pd

from analysis.cp import FIT_RANGE, fit_cp, fit_r2

CP, W_PRIME = 300.0, 20_000.0


class TestFitCP(unittest.TestCase):
    def test_recovers_synthetic_parameters(self):
        durs = [120, 180, 300, 480, 600, 900, 1200]
        mmp = pd.DataFrame({"power": [CP + W_PRIME / t for t in durs]},
                           index=durs)
        cp, w = fit_cp(mmp)
        self.assertAlmostEqual(cp, CP, delta=CP * 0.001)
        self.assertAlmostEqual(w, W_PRIME, delta=W_PRIME * 0.001)

    def test_ignores_points_outside_fit_range(self):
        durs = [5, 30, 120, 180, 300, 600, 1200, 3600]
        power = [CP + W_PRIME / t for t in durs]
        power[0] = 9999  # absurd sprint value must not affect the fit
        power[-1] = 1  # nor a bad long-duration point
        mmp = pd.DataFrame({"power": power}, index=durs)
        cp, w = fit_cp(mmp)
        self.assertAlmostEqual(cp, CP, delta=CP * 0.001)
        self.assertTrue(FIT_RANGE[0] > 30 and FIT_RANGE[1] < 3600)


class TestFitR2(unittest.TestCase):
    def test_perfect_hyperbola_scores_one(self):
        durs = [120, 180, 300, 480, 600, 900, 1200]
        mmp = pd.DataFrame({"power": [CP + W_PRIME / t for t in durs]},
                           index=durs)
        self.assertAlmostEqual(fit_r2(mmp), 1.0, places=9)

    def test_noisy_point_lowers_r2(self):
        durs = [120, 180, 300, 480, 600, 900, 1200]
        power = [CP + W_PRIME / t for t in durs]
        power[3] += 30  # one 30 W outlier
        mmp = pd.DataFrame({"power": power}, index=durs)
        self.assertLess(fit_r2(mmp), 0.99)


if __name__ == "__main__":
    unittest.main()
