"""`arena` CLI — run, demo, board.

  arena demo                          # offline brawl between two mocks -> gif
  arena run TASK --offline            # same, your own task
  arena run TASK --players "openai:gpt-5-mini,openai:claude-sonnet-4-5"
  arena board                         # elo leaderboard
"""
from __future__ import annotations

import argparse
import sys
import time

from . import __version__, battle, elo, gif, store
from . import render as R
from .players import build


def _score_map() -> dict:
    return {"1": 1.0, "2": 0.0, "t": 0.5}


def read_vote() -> str:
    """Single keystroke vote. Falls back to 'q' when stdin isn't a tty."""
    if not sys.stdin.isatty():
        return "q"
    import termios
    import tty

    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd)
        while True:
            ch = sys.stdin.read(1)
            if ch in "12tqQ\x03":
                sys.stdout.write("\n")
                return ch.lower()
    finally:
        termios.tcsetattr(fd, old)


def _players_from_args(args) -> list:
    if args.offline:
        return [build("mock:sprint"), build("mock:verbose")]
    spec = (args.players or "").strip()
    if spec:
        try:
            pls = [build(s.strip()) for s in spec.split(",") if s.strip()]
        except ValueError as e:
            raise SystemExit(f"arena: {e}")
        if len(pls) < 2:
            raise SystemExit("arena: --players needs at least 2 fighters, comma-separated")
        return pls
    raise SystemExit(
        'arena: give me fighters — use --offline for mocks, or '
        '--players "openai:gpt-5-mini,openai:claude-sonnet-4-5"'
    )


def cmd_run(args) -> int:
    task = " ".join(args.task).strip()
    if not task:
        raise SystemExit("arena: empty task")
    players = _players_from_args(args)

    print(f"\n⚔ ARENA — {' vs '.join(p.name for p in players)}\n", flush=True)
    runners, frames = battle.fight(players, task)

    if args.no_gif:
        out = None
    else:
        out = args.out or time.strftime("arena-%Y%m%d-%H%M.gif")
        path = gif.export(frames, out)
        print(f"  📎 replay: {path}")

    if args.auto or args.winner is not None:
        score_a = 0.5 if args.winner is None else float(args.winner)
    else:
        print("", flush=True)
        ch = read_vote()
        if ch in "q\x03":
            print("  ✋ aborted — no elo touched")
            return 130
        score_a = _score_map()[ch]
        how = ch

    with store.conn() as c:
        ra = store.rating(c, runners[0].player.name)
        rb = store.rating(c, runners[1].player.name)
        new_a, new_b = elo.update(ra, rb, score_a)
        store.update(
            c, runners[0].player.name, runners[1].player.name, score_a, (new_a, new_b)
        )

    changes = [
        (ra, new_a, new_a > new_b),
        (rb, new_b, new_b > new_a),
    ]
    tie = abs(new_a - new_b) < 1e-9
    for runner, (before, new_rating, beat) in zip(runners, changes):
        verdict, color = ("tie", 4) if tie else (("win", 2) if beat else ("loss", 1))
        print(
            R.paint(
                [
                    R.Seg(f"  {verdict} {runner.player.name:<34}", color, True),
                    R.Seg(f"{before:>6.0f} → {new_rating:.1f}", 7, False),
                ]
            )
        )
    _print_board()
    return 0


def cmd_demo(args) -> int:
    args.offline, args.players = True, ""
    args.auto, args.winner = True, None
    args.task = ["Conserte o parser de CSV que quebra espaços em strings citadas"]
    args.out = args.out or "assets/demo.gif"
    args.no_gif = False
    return cmd_run(args)


def _print_board(n: int = 6) -> None:
    with store.conn() as c:
        rows = store.top(c, n)
    if not rows:
        print("  board: (empty — run `arena demo`)")
        return
    print(R.paint([R.Seg(f"\n  {'fighter':<32}{'elo':>5}{'W':>4}{'L':>4}{'T':>4}", 3, True)]))
    for name, er, w, l, t in rows:
        print(f"  {name:<32}{er:>5}{w:>4}{l:>4}{t:>4}")


def cmd_board(_args) -> int:
    _print_board(n=20)
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="arena",
        description="AI agents fight in your terminal. You judge. Elo is public.",
    )
    ap.add_argument("--version", action="version", version=f"arena {__version__}")
    sub = ap.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("run", help="make two agents fight over a task")
    r.add_argument("task", nargs="+", help="the task they must solve")
    r.add_argument("--players", default="", help='"mock:sprint,openai:gpt-5-mini" — comma-separated')
    r.add_argument("--offline", action="store_true", help="two built-in mocks, no keys needed")
    r.add_argument("--auto", action="store_true", help="skip the vote, record a tie (demos/CI)")
    r.add_argument("--winner", type=int, choices=(0, 1), default=None,
                   help="pre-decide the winner index (non-interactive)")
    r.add_argument("--no-gif", action="store_true", help="skip the GIF replay export")
    r.add_argument("-o", "--out", default="", help="GIF output path")
    r.set_defaults(func=cmd_run)

    d = sub.add_parser("demo", help="instant offline brawl, replay saved to assets/demo.gif")
    d.add_argument("-o", "--out", default="", help="GIF output path")
    d.set_defaults(func=cmd_demo)

    b = sub.add_parser("board", help="print the elo leaderboard")
    b.set_defaults(func=cmd_board)

    args = ap.parse_args(argv)
    try:
        return args.func(args)
    except KeyboardInterrupt:
        print("\n  ✋ aborted")
        return 130
