"""Long-run progression must not merge the same ISO week of different years."""
import contextlib
import io
import os
import tempfile
import unittest

from analysis import volume


class TestYearCrossingWeeks(unittest.TestCase):
    def setUp(self):
        self.cwd = os.getcwd()
        self.tmp = tempfile.mkdtemp()
        os.makedirs(f"{self.tmp}/data")
        os.chdir(self.tmp)

    def tearDown(self):
        os.chdir(self.cwd)

    def test_same_iso_week_different_years(self):
        # two long runs exactly 364 days apart: same weekday, same ISO week
        # number, different years -> both must survive the groupby
        with open("data/runs.csv", "w") as f:
            f.write("activityId,startTimeLocal,distance,duration,averageHR\n"
                    "1,2026-05-15 10:00:00,10000,3600,150\n"
                    "2,2027-05-14 10:00:00,12000,4300,150\n")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            volume.main()
        self.assertIn("10.0 → 12.0", out.getvalue())


if __name__ == "__main__":
    unittest.main()
