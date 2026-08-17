#!/usr/bin/env python3
"""Determinism gate for M0: same (config, seed) must yield identical final state."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from project_one import Config, Simulation  # noqa: E402


def main() -> None:
    for condition in ("A", "C", "F", "N"):
        cfg = Config(condition=condition, steps=500, initial_population=100)
        h = []
        for _ in range(2):
            sim = Simulation(cfg, seed=123)
            sim.run()
            h.append(sim.state_hash())
        status = "OK " if h[0] == h[1] else "FAIL"
        print(f"[{status}] condition {condition}: {h[0][:16]}…")
        if h[0] != h[1]:
            sys.exit(1)
    print("Seed replay verified: identical state hashes across re-runs.")


if __name__ == "__main__":
    main()
