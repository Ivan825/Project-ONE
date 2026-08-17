#!/usr/bin/env python3
"""M3 flagship campaign: all conditions x paired seeds, standardized shock.

    python scripts/campaign.py --seeds 50 --steps 4000 --shock-step 2000 \
        --out campaigns/flagship

Design (pre-registered in docs/PLAN.md):
  Conditions A, B, C, F(invert), N; paired seeds (same seed list per condition);
  standardized disturbance (targeted hub removal) at --shock-step.
Each run writes one JSON summary: config, S(t) trajectory, broadcast trajectory,
final state hash. Full event logs are not stored at campaign scale.
"""
import argparse
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

CONDITIONS = ["A", "B", "C", "F", "N"]


def one_run(args):
    cond, seed, steps, shock_step, distortion, outdir = args
    from project_one import Config, Simulation
    cfg = Config(condition=cond, distortion=distortion, steps=steps,
                 shock_step=shock_step, snapshot_interval=0)
    sim = Simulation(cfg, seed=seed)
    sim.run()
    summary = {
        "condition": cond, "seed": seed, "steps": steps,
        "shock_step": shock_step, "distortion": distortion if cond == "F" else None,
        "observer_interval": cfg.observer_interval,
        "final_population": sim.population(),
        "state_hash": sim.state_hash(),
        "globals": sim.global_memory,
        "broadcasts": sim.broadcast_memory,
    }
    path = os.path.join(outdir, "runs", f"{cond}_s{seed}.json")
    with open(path, "w") as f:
        json.dump(summary, f)
    return cond, seed, sim.population()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=50)
    ap.add_argument("--steps", type=int, default=4000)
    ap.add_argument("--shock-step", type=int, default=2000)
    ap.add_argument("--distortion", default="invert",
                    choices=["invert", "crisis", "utopia"])
    ap.add_argument("--conditions", default=",".join(CONDITIONS))
    ap.add_argument("--out", default="campaigns/flagship")
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 1))
    args = ap.parse_args()

    conditions = args.conditions.split(",")
    os.makedirs(os.path.join(args.out, "runs"), exist_ok=True)
    manifest = {
        "design": "paired seeds across conditions; standardized hub-removal shock",
        "conditions": conditions, "seeds": list(range(1, args.seeds + 1)),
        "steps": args.steps, "shock_step": args.shock_step,
        "distortion": args.distortion,
        "primary_outcomes": [
            "recovery_time_90 (population, post-shock)",
            "fragmentation_post (mean, post-shock)",
            "cooperation_rate (mean, post-transient)",
            "self_model_convergence (drift toward broadcast)",
        ],
    }
    with open(os.path.join(args.out, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)

    jobs = [(c, s, args.steps, args.shock_step, args.distortion, args.out)
            for c in conditions for s in range(1, args.seeds + 1)]
    # Skip already-completed runs so the campaign is resumable.
    jobs = [j for j in jobs if not os.path.exists(
        os.path.join(args.out, "runs", f"{j[0]}_s{j[1]}.json"))]
    print(f"{len(jobs)} runs to execute on {args.workers} workers")

    t0, done = time.time(), 0
    with ProcessPoolExecutor(max_workers=args.workers) as ex:
        futures = [ex.submit(one_run, j) for j in jobs]
        for fut in as_completed(futures):
            cond, seed, pop = fut.result()
            done += 1
            if done % 10 == 0 or done == len(jobs):
                rate = done / (time.time() - t0)
                eta = (len(jobs) - done) / rate if rate else 0
                print(f"  {done}/{len(jobs)}  (last: {cond} s{seed} pop={pop})"
                      f"  ETA {eta/60:.1f} min")
    print(f"campaign complete in {(time.time()-t0)/60:.1f} min -> {args.out}/runs/")


if __name__ == "__main__":
    main()
