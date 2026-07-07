"""beats_saved: hand-computed bpm reduction from an efficiency gain."""
import unittest

from analysis.fitness import beats_saved


class TestBeatsSaved(unittest.TestCase):
    def test_hand_computed(self):
        # 150 bpm, efficiency 1.0 -> 1.1 m/beat: same speed needs the old
        # beat rate scaled by e1/e2, so 150 * (1 - 1/1.1) = 13.636... bpm
        self.assertAlmostEqual(beats_saved(150, 1.0, 1.1), 150 * (1 - 1 / 1.1))
        self.assertAlmostEqual(beats_saved(150, 1.0, 1.1), 13.636, places=3)

    def test_no_gain_no_savings(self):
        self.assertEqual(beats_saved(150, 1.0, 1.0), 0)


if __name__ == "__main__":
    unittest.main()
