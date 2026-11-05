import unittest

from arena_brawl import elo


class TestElo(unittest.TestCase):
    def test_standard_first_battle(self):
        self.assertEqual(elo.update(1000.0, 1000.0, 1.0), (1012.0, 988.0))

    def test_tie_between_equals(self):
        self.assertEqual(elo.update(1000.0, 1000.0, 0.5), (1000.0, 1000.0))

    def test_upset_is_worth_more(self):
        upset = elo.update(1000.0, 1200.0, 1.0)      # underdog wins
        expected = elo.update(1200.0, 1000.0, 1.0)  # favorite wins
        self.assertGreater(upset[0] - 1000.0, expected[0] - 1200.0)

    def test_bogus_score_rejected(self):
        with self.assertRaises(ValueError):
            elo.update(1000.0, 1000.0, 0.7)


if __name__ == "__main__":
    unittest.main()
