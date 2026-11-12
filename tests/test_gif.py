import os
import tempfile
import unittest

from PIL import Image

from arena_brawl import render
from arena_brawl.gif import export
from arena_brawl.render import Seg

def synth_frames(n=4):
    cols = [
        render.ColState(name="mock:sprint", color=2, text="def fix():\n    return ok — " * 30, chars=900),
        render.ColState(name="mock:verbose", color=3, text="# analysis\n1. think\n2. code\n3. test", chars=350),
    ]
    return [render.make_frame(cols, "ustria: fix csv", status=render.progress_row(cols)) for _ in range(n)]

class TestGif(unittest.TestCase):
    def test_export_creates_animated_gif(self):
        from arena_brawl.gif import CELL_H, CELL_W

        with tempfile.TemporaryDirectory() as tmp:
            frames = synth_frames()
            path = export(frames, os.path.join(tmp, "replay.gif"), tick=0.2)
            self.assertTrue(os.path.exists(path))
            self.assertGreater(os.path.getsize(path), 1024)
            cols_n = max(
                sum(len(s.text) for s in row) for row in frames[0]  # widest row
            )
            with Image.open(path) as im:
                self.assertTrue(im.is_animated)
                self.assertGreaterEqual(im.n_frames, 3)
                self.assertEqual(im.size, (cols_n * CELL_W, len(frames[0]) * CELL_H))

    def test_empty_frames_rejected(self):
        with self.assertRaises(ValueError):
            export([], "never-created.gif")

if __name__ == "__main__":
    unittest.main()
