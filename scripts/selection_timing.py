#!/usr/bin/env python3
"""Why the two measurements of selection on rho disagree.

The main campaign leaves one thing unreconciled. The ACCUMULATED shift in
rho-bar (H8) is large and highly significant -- the share channel falls from
1.08 to 0.24 under the inverted lie -- while the per-generation selection
differential S(rho) pooled over the run (H7) is mostly null, and null in that
very cell. Reporting only the half that worked would be the easy move; this
script asks instead whether the two are actually inconsistent.

They are not. The hypothesis is that selection against the costly response is
a SWEEP THAT COMPLETES: strong while standing variation in rho exists, then
close to nothing once rho has collapsed and the variance is spent. Pooling S
over the whole run averages a strong early signal with a spent late one, which
is exactly how a large cumulative shift and a weak pooled differential coexist.

That is testable without any new architecture: split the cohort window and
measure S, and the standing variation it acts on, in each half.

Condition A is the control throughout -- rho is causally inert there, so its
S is the sampling floor in both windows.

    python scripts/selection_timing.py
"""
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor

import numpy as np
from scipy.stats import wilcoxon

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))
from project_one import Config, Simulation            # noqa: E402
from project_one.agents import POLARITY_KEYS          # noqa: E402

OUT = os.path.join(ROOT, "campaigns", "policy_campaign")
SEEDS = 20
STEPS, SHOCK = 4000, 2000
GAIN, SHOCK_FRACTION = 0.8, 0.4
WINDOWS = {"early": (200, 1200), "late": (3000, 4000)}
CONDITIONS = [("A", ""), ("C", ""), ("F", "invert"), ("N", "")]


def one(job):
    cond, dist, seed = job
    cfg = Config(condition=cond, distortion=dist or "invert", steps=STEPS,
                 shock_step=SHOCK, shock_fraction=SHOCK_FRACTION,
                 feedback_gain=GAIN, policy_mode="polarity",
                 policy_log_interval=500, snapshot_interval=0)
    sim = Simulation(cfg, seed=seed)
    sim.run()
    out = {"cond": cond, "seed": seed}
    for tag, (t0, t1) in WINDOWS.items():
        coh = [a for a in sim.agents.values()
               if a.policy and a.death_time is not None
               and a.birth_time >= t0 and a.death_time <= t1]
        out[f"n_{tag}"] = len(coh)
        if len(coh) < 50:
            continue
        n = np.array([a.offspring_count for a in coh], float)
        if n.mean() <= 0:
            continue
        for k in POLARITY_KEYS:
            z = np.array([a.policy[k] for a in coh], float)
            out[f"S_{tag}_{k}"] = float(np.cov(z, n, bias=True)[0, 1] / n.mean())
            # The raw material selection has to work with. A sweep that
            # completes spends it.
            out[f"sd_{tag}_{k}"] = float(z.std())
    return out


def main():
    jobs = [(c, d, s) for c, d in CONDITIONS for s in range(1, SEEDS + 1)]
    workers = max(1, os.cpu_count() or 2)
    print(f"selection timing: {len(jobs)} runs on {workers} workers", flush=True)
    with ProcessPoolExecutor(max_workers=workers) as ex:
        rows = list(ex.map(one, jobs))

    def paired(cond, tag, k):
        a = {r["seed"]: r[f"S_{tag}_{k}"] for r in rows
             if r["cond"] == "A" and f"S_{tag}_{k}" in r}
        b = {r["seed"]: r[f"S_{tag}_{k}"] for r in rows
             if r["cond"] == cond and f"S_{tag}_{k}" in r}
        s = sorted(set(a) & set(b))
        if len(s) < 5:
            return None
        d = np.array([b[x] - a[x] for x in s])
        try:
            _, p = wilcoxon(d)
        except ValueError:
            p = 1.0
        return {"n": len(s), "median": float(np.median(d)), "p": float(p)}

    report = {"seeds": SEEDS, "windows": WINDOWS, "cells": {}, "variation": {}}
    print(f"\nS(rho) vs A, by window   (early = {WINDOWS['early']}, "
          f"late = {WINDOWS['late']})")
    print(f"  {'cond':>4} {'channel':>9} {'early':>10} {'p':>8}   "
          f"{'late':>10} {'p':>8}   ratio")
    for cond, _ in CONDITIONS[1:]:
        for k in POLARITY_KEYS:
            e, l = paired(cond, "early", k), paired(cond, "late", k)
            if not (e and l):
                continue
            report["cells"].setdefault(cond, {})[k] = {"early": e, "late": l}
            ratio = (abs(e["median"]) / abs(l["median"])
                     if l["median"] else float("inf"))
            print(f"  {cond:>4} {k:>9} {e['median']:+10.5f} {e['p']:8.4f}   "
                  f"{l['median']:+10.5f} {l['p']:8.4f}   {ratio:5.1f}x")

    print("\nstanding variation in rho across agents (what selection acts on)")
    print(f"  {'cond':>4} {'channel':>9} {'early sd':>10} {'late sd':>10} {'spent':>8}")
    for cond, _ in CONDITIONS:
        for k in POLARITY_KEYS:
            e = [r[f"sd_early_{k}"] for r in rows
                 if r["cond"] == cond and f"sd_early_{k}" in r]
            l = [r[f"sd_late_{k}"] for r in rows
                 if r["cond"] == cond and f"sd_late_{k}" in r]
            if not (e and l):
                continue
            em, lm = float(np.median(e)), float(np.median(l))
            report["variation"].setdefault(cond, {})[k] = {"early_sd": em,
                                                           "late_sd": lm}
            print(f"  {cond:>4} {k:>9} {em:10.4f} {lm:10.4f} "
                  f"{100 * (1 - lm / em):7.0f}%")

    dest = os.path.join(OUT, "selection_timing.json")
    with open(dest, "w") as f:
        json.dump({**report, "rows": rows}, f, indent=1)
    print(f"\nwrote {dest}")


if __name__ == "__main__":
    main()
