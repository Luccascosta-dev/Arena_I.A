"""The brawl itself: every player streams in its own thread while the main
thread samples the ring every `tick` seconds — each sample becomes both a
terminal progress line and one frozen frame for the GIF replay."""
from __future__ import annotations

import sys
import threading
import time

from . import render as R
from .render import ColState, Seg


class _Runner:
    def __init__(self, player, color: int):
        self.player = player
        self.state = ColState(name=player.name, color=color)
        self.lock = threading.Lock()
        self.done = False
        self._thread: threading.Thread | None = None

    def start(self, task: str) -> None:
        self._thread = threading.Thread(target=self._work, args=(task,), daemon=True)
        self._thread.start()

    def _work(self, task: str) -> None:
        try:
            for chunk in self.player.stream(task):
                with self.lock:
                    self.state.text += chunk
                    self.state.chars = len(self.state.text)
        except Exception as e:  # surface the failure inside its own pane
            with self.lock:
                self.state.err = f"{type(e).__name__}: {e}"[:200]
        finally:
            with self.lock:
                self.done = True

    def join(self) -> None:
        if self._thread:
            self._thread.join()

    @property
    def finished(self) -> bool:
        with self.lock:
            return self.done

    def snapshot(self) -> ColState:
        with self.lock:
            return ColState(
                name=self.state.name,
                color=self.state.color,
                text=self.state.text,
                chars=self.state.chars,
                err=self.state.err,
            )


VOTE_FOOTER = [
    Seg(" vote: ", 3, True),
    Seg("[1]", 7, True), Seg(" left pane   ", 7, False),
    Seg("[2]", 7, True), Seg(" right pane   ", 7, False),
    Seg("[t]", 7, True), Seg(" tie   ", 7, False),
    Seg("[q]", 7, True), Seg(" abort", 7, False),
]

COLORS = (2, 3, 4, 5, 6, 1)  # green, yellow, blue, magenta, cyan, red …


def fight(players, task: str, tick: float = 0.22):
    """Race the players. Returns (runners, frames)."""
    runners = [_Runner(p, COLORS[i % len(COLORS)]) for i, p in enumerate(players)]
    frames: list[list[list[Seg]]] = []
    live = sys.stdout.isatty()
    for r in runners:
        r.start(task)
    try:
        while not all(r.finished for r in runners):
            time.sleep(tick)
            snaps = [r.snapshot() for r in runners]
            frames.append(R.make_frame(snaps, task, status=R.progress_row(snaps)))
            if live:
                line = "   ".join(f"{s.name}: {s.chars}c" for s in snaps)
                print(f"\r  {line[:110]}", end="", flush=True)
    finally:
        for r in runners:
            r.join()
    if live:
        print()

    snaps = [r.snapshot() for r in runners]
    frames.append(
        R.make_frame(snaps, task, status=R.progress_row(snaps), footer=VOTE_FOOTER)
    )
    return runners, frames
