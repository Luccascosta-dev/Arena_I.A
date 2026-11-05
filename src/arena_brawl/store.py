"""SQLite leaderboard. Lives in ~/.arena-brawl (or $ARENA_HOME)."""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path


def db_dir() -> Path:
    base = os.environ.get("ARENA_HOME")
    d = Path(base) if base else Path.home() / ".arena-brawl"
    d.mkdir(parents=True, exist_ok=True)
    return d


def conn() -> sqlite3.Connection:
    c = sqlite3.connect(str(db_dir() / "book.db"))
    c.execute(
        """create table if not exists players (
            name    text primary key,
            elo     real not null default 1000,
            wins    integer not null default 0,
            losses  integer not null default 0,
            ties    integer not null default 0
        )"""
    )
    c.commit()
    return c


def ensure(c: sqlite3.Connection, name: str) -> None:
    c.execute("insert or ignore into players (name) values (?)", (name,))
    c.commit()


def rating(c: sqlite3.Connection, name: str) -> float:
    ensure(c, name)
    (elo,) = c.execute("select elo from players where name = ?", (name,)).fetchone()
    return float(elo)


def update(
    c: sqlite3.Connection, a: str, b: str, score_a: float, ratings: tuple[float, float]
) -> None:
    """ratings: ABSOLUTE new ratings from elo.update — (new_a, new_b).
    score_a: 1 = A won, 0 = B won, 0.5 = tie. One counter moves per player."""
    ensure(c, a)
    ensure(c, b)
    for name, new_elo, stat in (
        (a, ratings[0], "losses" if score_a == 0.0 else ("ties" if score_a == 0.5 else "wins")),
        (b, ratings[1], "wins" if score_a == 0.0 else ("ties" if score_a == 0.5 else "losses")),
    ):
        c.execute(
            f"update players set elo = ?, {stat} = {stat} + 1 where name = ?",
            (new_elo, name),
        )
    c.commit()


def top(c: sqlite3.Connection, n: int = 10) -> list[tuple]:
    ensure_rows(c)
    return c.execute(
        "select name, cast(elo as int), wins, losses, ties "
        "from players order by elo desc limit ?",
        (n,),
    ).fetchall()


def ensure_rows(c: sqlite3.Connection) -> None:
    c.commit()


def reset(c: sqlite3.Connection) -> None:
    c.execute("delete from players")
    c.commit()
