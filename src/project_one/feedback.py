"""Feedback module: decides what agents actually receive, per condition.

Conditions:
  A - no observer output at all
  B - observer runs, agents receive nothing
  C - agents receive the accurate self-model
  F - agents receive a systematically distorted self-model
  N - agents receive a matched-bandwidth random signal (same keys, same ranges)
"""
from __future__ import annotations

# Keys broadcast to agents (subset of S(t)); all normalized to [0,1]
BROADCAST_KEYS = ("fragmentation", "centralization", "cooperation", "inequality", "turnover")


def make_broadcast(condition: str, s_t: dict, rng, distortion: str) -> dict | None:
    if condition in ("A", "B"):
        return None
    if condition == "C":
        return {k: s_t[k] for k in BROADCAST_KEYS}
    if condition == "F":
        return _distort(s_t, distortion)
    if condition == "N":
        # Matched bandwidth: same message shape, values drawn uniformly.
        return {k: rng.random() for k in BROADCAST_KEYS}
    raise ValueError(f"Unknown condition: {condition}")


def _distort(s_t: dict, mode: str) -> dict:
    if mode == "invert":
        return {k: 1.0 - s_t[k] for k in BROADCAST_KEYS}
    if mode == "crisis":
        return {"fragmentation": 0.9, "centralization": 0.9, "cooperation": 0.1,
                "inequality": 0.9, "turnover": 0.9}
    if mode == "utopia":
        return {"fragmentation": 0.05, "centralization": 0.2, "cooperation": 0.9,
                "inequality": 0.1, "turnover": 0.2}
    raise ValueError(f"Unknown distortion mode: {mode}")
