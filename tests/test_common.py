"""fmt_pace edges, load_stream gap policy, load_runs derived columns."""
import json
import os
import tempfile
import unittest

from analysis.common import fmt_pace, load_runs, load_stream


class TestFmtPace(unittest.TestCase):
    def test_exact(self):
        self.assertEqual(fmt_pace(360), "6:00/km")

    def test_rounds_down(self):
        self.assertEqual(fmt_pace(359.4), "5:59/km")

    def test_rounds_up(self):
        self.assertEqual(fmt_pace(359.6), "6:00/km")


class TestLoadRunsDerived(unittest.TestCase):
    def test_derived_columns(self):
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False) as f:
            f.write("activityId,startTimeLocal,distance,duration,averageHR\n"
                    "1,2026-01-01 10:00:00,5000,1500,150\n")
            path = f.name
        try:
            df = load_runs(path)
            self.assertAlmostEqual(df["km"].iloc[0], 5.0)
            self.assertAlmostEqual(df["pace_s"].iloc[0], 300.0)  # 5:00/km
            # 5000 m / (150 bpm * 25 min) of beats
            self.assertAlmostEqual(df["m_per_beat"].iloc[0], 5000 / (150 * 25))
        finally:
            os.unlink(path)


class TestLoadStreamGaps(unittest.TestCase):
    """Recording gaps <=15 s are interpolated; longer gaps keep NaNs."""

    def setUp(self):
        self.cwd = os.getcwd()
        self.tmp = tempfile.mkdtemp()
        os.makedirs(f"{self.tmp}/data/streams")
        os.chdir(self.tmp)

    def tearDown(self):
        os.chdir(self.cwd)

    def test_gap_policy(self):
        t0 = 1_700_000_000_000  # arbitrary epoch ms
        secs = list(range(0, 11)) + list(range(21, 31)) + list(range(51, 61))
        stream = {"directTimestamp": [t0 + s * 1000 for s in secs],
                  "directPower": [float(s) for s in secs],
                  "directSpeed": [3.0] * len(secs),
                  "directHeartRate": [150.0] * len(secs)}
        with open("data/streams/42.json", "w") as f:
            json.dump(stream, f)

        s = load_stream(42)
        self.assertEqual(len(s), 61)  # resampled to full 1 s index
        # 10 s gap (11..20) fully interpolated, linear so equals the second
        self.assertFalse(s.loc[11:20, "power"].isna().any())
        self.assertAlmostEqual(s.loc[15, "power"], 15.0)
        # 20 s gap (31..50): interpolate(limit=15) leaves the tail NaN
        self.assertTrue(s.loc[31:50, "power"].isna().any())
        self.assertEqual(s["power"].isna().sum(), 5)


if __name__ == "__main__":
    unittest.main()
