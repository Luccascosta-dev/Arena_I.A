"""Elo rating for the arena. K=24, standard two-player math."""
from __future__ import annotations

K = 24.0


def expected(ra: float, rb: float) -> float:
    return 1.0 / (1.0 + 10.0 ** ((rb - ra) / 400.0))


def update(ra: float, rb: float, score_a: float) -> tuple[float, float]:
    """score_a: 1 = A won, 0 = B won, 0.5 = tie. Returns (new_a, new_b)."""
    if score_a not in (0.0, 0.5, 1.0):
        raise ValueError(f"score must be 0, 0.5 or 1 — got {score_a}")
    ea = expected(ra, rb)
    na = ra + K * (score_a - ea)
    nb = rb + K * ((1.0 - score_a) - (1.0 - ea))
    return round(na, 1), round(nb, 1)
