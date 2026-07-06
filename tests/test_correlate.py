"""assemble(): runs left-joined with daily wellness and PMC values;
print_chapter(): Pearson r and NaN handling in the text output."""
import contextlib
import io
import unittest

import pandas as pd

from analysis.correlate import (CHAPTERS, assemble, list_columns,
                                print_chapter)

EMPTY = pd.Series(dtype=float)


def runs_frame(dates):
    return pd.DataFrame({"startTimeLocal": pd.to_datetime(dates),
                         "km": [10.0] * len(dates)})


def chapter_df(a, b):
    return pd.DataFrame({"date": pd.date_range("2026-06-01", periods=len(a)),
                         "a": a, "b": b})


def chapter_output(df, right=True):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        print_chapter(df, "t", [("a", "a")], [("b", "b")] if right else None)
    return out.getvalue()


class TestAssemble(unittest.TestCase):
    def test_wellness_joined_on_run_date(self):
        runs = runs_frame(["2026-06-02 08:00:00", "2026-06-05 08:00:00"])
        wellness = pd.DataFrame({"hrv": [55.0]},
                                index=pd.to_datetime(["2026-06-02"]))
        df = assemble(runs, wellness, EMPTY, EMPTY, EMPTY)
        self.assertEqual(df["hrv"].iloc[0], 55.0)
        self.assertTrue(pd.isna(df["hrv"].iloc[1]))

    def test_pmc_reindexed_to_run_dates(self):
        runs = runs_frame(["2026-06-03 07:00:00"])
        daily = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0],
                          index=pd.date_range("2026-06-01", periods=5))
        wellness = pd.DataFrame(index=pd.DatetimeIndex([]))
        df = assemble(runs, wellness, daily, daily, daily)
        self.assertEqual(df["tsb"].iloc[0], 3.0)

    def test_same_day_runs_share_wellness_and_rows_kept(self):
        runs = runs_frame(["2026-06-02 08:00:00", "2026-06-02 18:00:00",
                           "2026-06-04 08:00:00"])
        wellness = pd.DataFrame(
            {"hrv": [60.0, 50.0]},
            index=pd.to_datetime(["2026-06-02", "2026-06-04"]))
        df = assemble(runs, wellness, EMPTY, EMPTY, EMPTY)
        self.assertEqual(len(df), 3)
        self.assertEqual(list(df["hrv"]), [60.0, 60.0, 50.0])

    def test_run_date_outside_pmc_range_is_nan(self):
        runs = runs_frame(["2026-06-10 08:00:00"])
        daily = pd.Series([1.0, 2.0],
                          index=pd.date_range("2026-06-01", periods=2))
        wellness = pd.DataFrame(index=pd.DatetimeIndex([]))
        df = assemble(runs, wellness, daily, daily, daily)
        self.assertTrue(pd.isna(df["tsb"].iloc[0]))

    def test_late_evening_run_joins_same_calendar_day(self):
        runs = runs_frame(["2026-06-02 23:59:00"])
        wellness = pd.DataFrame({"hrv": [55.0]},
                                index=pd.to_datetime(["2026-06-02"]))
        df = assemble(runs, wellness, EMPTY, EMPTY, EMPTY)
        self.assertEqual(df["hrv"].iloc[0], 55.0)


class TestPrintChapter(unittest.TestCase):
    def test_perfect_correlation_and_nan_row(self):
        df = pd.DataFrame({
            "date": pd.date_range("2026-06-01", periods=4),
            "a": [1.0, 2.0, 3.0, 5.0],
            "b": [10.0, 20.0, 30.0, float("nan")],  # y = 10x where present
        })
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            print_chapter(df, "a vs b", [("a", "a")], [("b", "b")])
        text = out.getvalue()
        self.assertIn("r = +1.00 (n=3)", text)  # NaN row excluded from r
        self.assertIn("-", text.splitlines()[-1])  # but still printed as '-'

    def test_negative_correlation(self):
        text = chapter_output(chapter_df([1.0, 2.0, 3.0], [3.0, 2.0, 1.0]))
        self.assertIn("r = -1.00 (n=3)", text)

    def test_reference_r_value(self):
        # hand-computed Pearson: r = 9/sqrt(84) = 0.982
        text = chapter_output(chapter_df([1.0, 2.0, 3.0], [1.0, 2.0, 4.0]))
        self.assertIn("r = +0.98 (n=3)", text)

    def test_too_few_overlapping_points(self):
        text = chapter_output(chapter_df([1.0, 2.0], [1.0, 2.0]))
        self.assertIn("not enough overlapping data", text)

    def test_left_only_chapter_has_no_r(self):
        text = chapter_output(chapter_df([1.0, 2.0, 3.0], [0.0] * 3),
                              right=False)
        self.assertNotIn("r =", text)
        # title + header + one row per run
        self.assertEqual(len(text.strip().splitlines()), 5)


class TestChapters(unittest.TestCase):
    def test_specs_well_formed(self):
        for title, left, right in CHAPTERS:  # unpacking enforces 3-tuples
            self.assertIsInstance(title, str)
            self.assertTrue(left, "left axis needs at least one column")
            for col, label in left + (right or []):
                self.assertIsInstance(col, str)
                self.assertIsInstance(label, str)


class TestListColumns(unittest.TestCase):
    def test_only_numeric_columns_with_counts(self):
        df = pd.DataFrame({"km": [1.0, None], "status": ["ok", "bad"]})
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            list_columns(df)
        self.assertIn("km", out.getvalue())
        self.assertIn("1/2", out.getvalue())
        self.assertNotIn("status", out.getvalue())


if __name__ == "__main__":
    unittest.main()
