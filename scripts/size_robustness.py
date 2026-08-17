#!/usr/bin/env python3
"""Finite-size robustness check: do the core effects survive at ~2x system scale?

Doubles initial population AND resource capacity/regeneration (population is
resource-limited, so scale must be raised through the environment).

    python scripts/size_robustness.py --out campaigns/size2x
"""
import argparse
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

TOKENS = ["A", "C", "F:invert", "N"]


def one(args):
    token, seed, outdir = args
    from project_one import Config, Simulation
    cond, _, dist = token.partition(":")
    cfg = Config(condition=cond, distortion=dist or "invert",
                 steps=3000, shock_step=1500, shock_fraction=0.4,
                 initial_population=300, resource_capacity=12000.0,
                 resource_base_regen=120.0, snapshot_interval=0)
    sim = Simulation(cfg, seed=seed)
    sim.run()
    out = {"token": token, "condition": cond, "seed": seed, "steps": 3000,
           "shock_step": 1500, "feedback_gain": cfg.feedback_gain,
           "shock_fraction": 0.4, "observer_interval": cfg.observer_interval,
           "final_population": sim.population(),
           "globals": sim.global_memory, "broadcasts": sim.broadcast_memory}
    with open(os.path.join(outdir, "runs",
                           f"{token.replace(':', '-')}_s{seed}.json"), "w") as f:
        json.dump(out, f)
    return token, seed, sim.population()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=8)
    ap.add_argument("--out", default="campaigns/size2x")
    ap.add_argument("--workers", type=int, default=2)
    args = ap.parse_args()
    os.makedirs(os.path.join(args.out, "runs"), exist_ok=True)
    with open(os.path.join(args.out, "manifest.json"), "w") as f:
        json.dump({"design": "2x scale check", "conditions": TOKENS,
                   "seeds": list(range(1, args.seeds + 1)), "steps": 3000,
                   "shock_step": 1500, "feedback_gain": 0.8,
                   "distortion": "invert", "shock_fraction": 0.4,
                   "initial_population": 300, "resource_capacity": 12000}, f)
    jobs = [(t, s, args.out) for t in TOKENS for s in range(1, args.seeds + 1)
            if not os.path.exists(os.path.join(
                args.out, "runs", f"{t.replace(':', '-')}_s{s}.json"))]
    print(f"{len(jobs)} runs")
    with ProcessPoolExecutor(max_workers=args.workers) as ex:
        futs = [ex.submit(one, j) for j in jobs]
        done = 0
        for fut in as_completed(futs):
            t, s, p = fut.result()
            done += 1
            print(f"  {done}/{len(jobs)} {t} s{s} pop={p}", flush=True)


if __name__ == "__main__":
    main()
