#!/usr/bin/env python3
"""Run a single Project ONE simulation.

Examples:
    python run.py --condition C --steps 2000 --seed 42
    python run.py --condition F --distortion crisis --shock-step 1000 --seed 7
"""
import argparse
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from project_one import Config, Simulation  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description="Project ONE simulation")
    ap.add_argument("--condition", default="A", choices=list("ABCFN"))
    ap.add_argument("--distortion", default="invert",
                    choices=["invert", "crisis", "utopia"])
    ap.add_argument("--steps", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--population", type=int, default=150)
    ap.add_argument("--shock-step", type=int, default=0)
    ap.add_argument("--out", default=None, help="output dir (default runs/<auto>)")
    args = ap.parse_args()

    cfg = Config(condition=args.condition, distortion=args.distortion,
                 steps=args.steps, initial_population=args.population,
                 shock_step=args.shock_step)
    sim = Simulation(cfg, seed=args.seed)

    t0 = time.time()
    sim.run()
    dt = time.time() - t0

    out = args.out or os.path.join(
        "runs", f"{args.condition}_s{args.seed}_n{args.steps}")
    sim.save(out)

    last = sim.global_memory[-1] if sim.global_memory else {}
    print(f"condition={args.condition} seed={args.seed} steps={args.steps} "
          f"({dt:.1f}s)")
    print(f"final population: {sim.population()}   "
          f"events logged: {len(sim.events)}")
    if last:
        print("final S(t): " + ", ".join(
            f"{k}={v:.3f}" if isinstance(v, float) else f"{k}={v}"
            for k, v in last.items() if k != "t"))
    print(f"state hash: {sim.state_hash()[:16]}…")
    print(f"saved to {out}/")


if __name__ == "__main__":
    main()
