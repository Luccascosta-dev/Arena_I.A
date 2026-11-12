import unittest

from arena_brawl import render
from arena_brawl.players import MockPlayer, build

class TestPlayers(unittest.TestCase):
    def test_factory_builds_mocks(self):
        self.assertIsInstance(build("mock:sprint"), MockPlayer)
        with self.assertRaises(ValueError):
            build("nonsense")

    def test_mock_streams_everything(self):
        p = MockPlayer("sprint")
        chunks = list(p.stream("fix the csv parser"))
        text = "".join(chunks)
        self.assertTrue(len(text) > 300)
        self.assertIn("def split_csv_line", text)
        self.assertEqual(p.name, "mock:sprint")

    def test_verbose_mentions_task(self):
        p = MockPlayer("verbose")
        text = "".join(p.stream("banish the werewolf bug"))
        self.assertIn("werewolf", text)

class TestRender(unittest.TestCase):
    def test_frames_have_constant_shape(self):
        c1 = render.ColState(name="mock:a", color=2, text="short answer", chars=12)
        c2 = render.ColState(name="mock:b", color=3, text="x " * 400, chars=800)
        f1 = render.make_frame([c1, c2], "task")
        f2 = render.make_frame([c2, c1], "task")
        self.assertEqual(len(f1), len(f2))

    def test_no_row_overflows_canvas(self):
        c = render.ColState(name="mock:a", color=2, text="word " * 400)
        for rows in render.make_frame([c, c], "some barely medium task"):
            self.assertLessEqual(render.visible(rows), render.WIDTH)

    def test_picked_pads_to_max_lines(self):
        c = render.ColState(name="mock:a", color=2, text="little text")
        self.assertEqual(len(c.picked(30)), render.MAX_LINES)

    def test_paint_adds_ansi(self):
        out = render.paint([render.Seg("hi", 2, True)])
        self.assertIn("\x1b[32m", out)
        self.assertIn("\x1b[0m", out)

if __name__ == "__main__":
    unittest.main()
