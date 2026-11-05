import unittest

from arena_brawl import store


class TestStore(unittest.TestCase):
    def setUp(self):
        import os
        import tempfile

        self._tmp = tempfile.mkdtemp(prefix="arena-test-")
        self._old = os.environ.get("ARENA_HOME", "")
        os.environ["ARENA_HOME"] = self._tmp

    def tearDown(self):
        import os
        import shutil

        if self._old:
            os.environ["ARENA_HOME"] = self._old
        else:
            os.environ.pop("ARENA_HOME", None)
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_fresh_rating_is_1000(self):
        conn = store.conn()
        self.assertEqual(store.rating(conn, "mock:sprint"), 1000.0)

    def test_win_moves_counters(self):
        import arena_brawl.elo as elo

        conn = store.conn()
        store.update(conn, "a", "b", 1.0, elo.update(1000.0, 1000.0, 1.0))
        rows = {name: row for name, *row in store.top(conn, 10)}
        self.assertEqual(rows["a"][0], 1012)
        self.assertEqual(rows["b"][0], 988)
        self.assertEqual(rows["a"][1:], [1, 0, 0])
        self.assertEqual(rows["b"][1:], [0, 1, 0])

    def test_tie_moves_only_ties(self):
        import arena_brawl.elo as elo

        conn = store.conn()
        store.update(conn, "a", "b", 0.5, elo.update(1000.0, 1000.0, 0.5))
        rows = {name: row for name, *row in store.top(conn, 10)}
        self.assertEqual(rows["a"][0], 1000)
        self.assertEqual(rows["a"][1:], [0, 0, 1])
        self.assertEqual(rows["b"][1:], [0, 0, 1])

    def test_loss_case_not_inverted(self):
        import arena_brawl.elo as elo

        conn = store.conn()
        store.update(conn, "a", "b", 0.0, elo.update(1000.0, 1000.0, 0.0))
        rows = {name: row for name, *row in store.top(conn, 10)}
        self.assertEqual(rows["a"][1:], [0, 1, 0])   # a lost
        self.assertEqual(rows["b"][1:], [1, 0, 0])   # b won


if __name__ == "__main__":
    unittest.main()
