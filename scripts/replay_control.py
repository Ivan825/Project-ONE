#!/usr/bin/env python3
"""Structured-noise control (condition R): broadcast a GENUINE self-model
trajectory recorded from a different seed's observed-but-blind run. Preserves
realistic marginals and temporal coherence while breaking self-reference.

    python scripts/replay_control.py --out campaigns/replay_control

Comparison hierarchy this completes:
  true self-model (C) > false self-model (F) > replayed real self-model (R)
  > uniform noise (N) > nothing (A).
"""
import argparse
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

BKEYS = ("fragmentation", "centralization", "cooperation", "inequality",
         "turnover")
PARAMS = dict(steps=4000, shock_step=2000, shock_fraction=0.4,
              snapshot_interval=0)
N_LIB = 15


def library_run(seed):
    from project_one import Config, Simulation
    sim = Simulation(Config(condition="B", **PARAMS), seed=seed)
    sim.run()
    return seed, [{k: s[k] for k in BKEYS} for s in sim.global_memory]


def r_run(args):
    seed, traj, outdir = args
    from project_one import Config, Simulation
    cfg = Config(condition="R", replay_trajectory=traj, **PARAMS)
    sim = Simulation(cfg, seed=seed)
    sim.run()
    out = {"token": "R", "condition": "R", "seed": seed,
           "steps": PARAMS["steps"], "shock_step": PARAMS["shock_step"],
           "shock_fraction": PARAMS["shock_fraction"], "feedback_gain": 0.8,
           "observer_interval": 10, "distortion": None,
           "final_population": sim.population(),
           "globals": sim.global_memory, "broadcasts": sim.broadcast_memory}
    with open(os.path.join(outdir, "runs", f"R_s{seed}.json"), "w") as f:
        json.dump(out, f)
    return seed, sim.population()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=30)
    ap.add_argument("--out", default="campaigns/replay_control")
    ap.add_argument("--workers", type=int, default=2)
    args = ap.parse_args()
    os.makedirs(os.path.join(args.out, "runs"), exist_ok=True)

    lib_path = os.path.join(args.out, "library.json")
    if os.path.exists(lib_path):
        library = json.load(open(lib_path))
    else:
        library = {}
        with ProcessPoolExecutor(max_workers=args.workers) as ex:
            for fut in as_completed([ex.submit(library_run, 5000 + i)
                                     for i in range(1, N_LIB + 1)]):
                seed, traj = fut.result()
                library[str(seed)] = traj
                print(f"  library {len(library)}/{N_LIB}", flush=True)
        with open(lib_path, "w") as f:
            json.dump(library, f)

    keys = sorted(library)
    jobs = [(s, library[keys[(s - 1) % N_LIB]], args.out)
            for s in range(1, args.seeds + 1)
            if not os.path.exists(os.path.join(args.out, "runs", f"R_s{s}.json"))]
    with open(os.path.join(args.out, "manifest.json"), "w") as f:
        json.dump({"design": "replayed self-model control (paired with "
                             "harsh_shock seeds)", "conditions": ["R"],
                   "seeds": list(range(1, args.seeds + 1)),
                   "library_seeds": [5000 + i for i in range(1, N_LIB + 1)],
                   "distortion": None, "feedback_gain": 0.8,
                   **{k: PARAMS[k] for k in ("steps", "shock_step",
                                             "shock_fraction")}}, f, indent=2)
    print(f"{len(jobs)} R runs")
    done = 0
    with ProcessPoolExecutor(max_workers=args.workers) as ex:
        for fut in as_completed([ex.submit(r_run, j) for j in jobs]):
            seed, pop = fut.result()
            done += 1
            print(f"  R {done}/{len(jobs)} s{seed} pop={pop}", flush=True)


if __name__ == "__main__":
    main()
