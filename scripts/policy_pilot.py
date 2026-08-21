#!/usr/bin/env python3
"""Pilot for the evolved-policy architecture (v2) -- BASELINE ONLY.

Fixes the two free parameters of the v2 design (horizon, and the noise floor
against which any policy result must be read) using runs in which the policy
is INVISIBLE to selection, so nothing measured here can be contaminated by a
treatment outcome. This is the same discipline as the ecology ensemble's
viability screen, applied to the other paper.

Under condition A there is no broadcast at all. The heritable weight matrix W
therefore has no effect on any agent's behaviour, is under no selection
whatsoever, and every movement of the population mean W-bar is drift. That
makes A the exact null for every policy claim -- and it makes this pilot
readable without ever running C, F or N.

    --horizon   how many generations, and how much lineage diversity,
                each candidate run length buys
    --null      the drift distribution of dW-bar per cell, and the effect size
                a paired test could actually detect at each seed count

The decision rules are written down here BEFORE the pilot runs (see DECISION),
so choosing the horizon cannot be a choice about which result appears.
"""
import argparse
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))
from project_one import Config, Simulation           # noqa: E402
from project_one.agents import POLICY_KEYS           # noqa: E402

OUT = os.path.join(ROOT, "campaigns", "policy_pilot")

HORIZONS = [4000, 8000, 16000]     # 4000 is the paper's own horizon
HORIZON_SEEDS = 3
NULL_SEEDS = 16
SHOCK_FRACTION = 0.4
GAIN = 0.8

# --- PRE-REGISTERED DECISION RULES ----------------------------------------
# Fixed before the pilot ran. Both are about the measuring instrument, not
# about any effect: how much evolutionary time the run contains, and how much
# of the population's ancestry survives to carry variation.
DECISION = {
    "min_generations": 40,        # >= 2x the paper's ~20, for selection to act
    "min_lineage_effective_n": 3.0,   # ancestry not collapsed to a single line
    "note": ("Smallest horizon satisfying BOTH, at the median over seeds. "
             "Ties go to the smaller horizon: compute spent on length is "
             "compute not spent on paired seeds, and seeds are what beat drift."),
}

# OUTCOME, recorded rather than edited away: NO horizon satisfied this rule.
# lineage_effective_n FALLS as the horizon grows (1.92 -> 1.56 -> 1.00), because
# the population coalesces to a single founder line; longer runs coalesce
# harder. The rule was mis-specified, not merely unmet: coalescence to one
# lineage is the signature of strong selection, not evidence that selection
# cannot act, so requiring standing lineage diversity in order to MEASURE
# selection had the causality backwards.
#
# The threshold above is therefore left exactly as written and NOT relaxed --
# relaxing a pre-registered bound after watching it fail is the move the
# pre-registration exists to prevent. Instead the instrument is replaced by one
# that does not depend on lineage diversity at all (--selection-null below),
# and validated against a known null and a known positive control before any
# treatment condition is run. See docs/PAPER2_PLAN.md Sect. 2.2b-2.2c.


def cfg_for(steps, seed=None):
    return Config(condition="A", steps=steps, shock_step=steps // 2,
                  shock_fraction=SHOCK_FRACTION, feedback_gain=GAIN,
                  policy_mode="evolved", policy_log_interval=max(1, steps // 8),
                  snapshot_interval=0)


def one(job):
    steps, seed = job
    sim = Simulation(cfg_for(steps), seed=seed)
    sim.run()
    g = sim.global_memory
    full = [s for s in g if "mean_policy" in s]
    w0, w1 = full[0]["mean_policy"], full[-1]["mean_policy"]
    lin = [s["lineage_effective_n"] for s in g if "lineage_effective_n" in s]
    return {
        "steps": steps, "seed": seed,
        "max_generation": max((a.generation for a in sim.agents.values()),
                              default=0),
        "final_population": g[-1].get("population", 0),
        "lineage_effective_n_median": float(np.median(lin)) if lin else None,
        "lineage_effective_n_final": (lin[-1] if lin else None),
        "policy_norm_first": full[0]["policy_norm"],
        "policy_norm_last": full[-1]["policy_norm"],
        # The quantity every v2 claim is built from, measured where it is
        # guaranteed to be pure drift.
        "dW": {k: w1[k] - w0[k] for k in POLICY_KEYS},
        "state_hash": sim.state_hash(),
    }


def execute(jobs, label):
    workers = max(1, (os.cpu_count() or 2))
    print(f"{label}: {len(jobs)} runs on {workers} workers", flush=True)
    rows, done = [], 0
    with ProcessPoolExecutor(max_workers=workers) as ex:
        futs = [ex.submit(one, j) for j in jobs]
        for f in as_completed(futs):
            rows.append(f.result())
            done += 1
            print(f"  {done}/{len(jobs)}", flush=True)
    return rows


def horizon():
    os.makedirs(OUT, exist_ok=True)
    jobs = [(h, s) for h in HORIZONS for s in range(1, HORIZON_SEEDS + 1)]
    rows = execute(jobs, "horizon pilot (baseline only)")

    print(f"\n{'steps':>7} {'gens':>6} {'lineage_eff_n':>14} {'pop':>6} "
          f"{'|W| drift':>10}")
    summary = {}
    for h in HORIZONS:
        mine = [r for r in rows if r["steps"] == h]
        gens = float(np.median([r["max_generation"] for r in mine]))
        lin = float(np.median([r["lineage_effective_n_median"] for r in mine]))
        pop = float(np.median([r["final_population"] for r in mine]))
        drift = float(np.median([r["policy_norm_last"] - r["policy_norm_first"]
                                 for r in mine]))
        summary[h] = {"generations": gens, "lineage_effective_n": lin,
                      "population": pop, "policy_norm_drift": drift,
                      "meets": bool(gens >= DECISION["min_generations"]
                                    and lin >= DECISION["min_lineage_effective_n"])}
        print(f"{h:7d} {gens:6.0f} {lin:14.2f} {pop:6.0f} {drift:+10.4f}"
              f"   {'OK' if summary[h]['meets'] else '-'}")

    passing = [h for h in HORIZONS if summary[h]["meets"]]
    chosen = min(passing) if passing else None
    print(f"\nchosen horizon: {chosen if chosen else 'NONE MEET THE RULE'}")
    if chosen is None:
        print("  -> the rule says extend HORIZONS rather than relax the rule.")
    dest = os.path.join(OUT, "horizon.json")
    with open(dest, "w") as f:
        json.dump({"decision_rules": DECISION, "summary": summary,
                   "chosen_horizon": chosen, "rows": rows}, f, indent=1)
    print(f"wrote {dest}")


def null(steps=None):
    with open(os.path.join(OUT, "horizon.json")) as f:
        h = json.load(f)
    steps = steps or h["chosen_horizon"]
    if steps is None:
        sys.exit("no horizon chosen; run --horizon first")
    jobs = [(steps, s) for s in range(101, 101 + NULL_SEEDS)]
    rows = execute(jobs, f"drift null at {steps} steps (baseline only)")

    # Per-cell drift distribution. Under A this is entirely drift: W cannot
    # affect behaviour when no broadcast exists.
    per_cell = {k: np.array([r["dW"][k] for r in rows]) for k in POLICY_KEYS}
    sds = np.array([v.std(ddof=1) for v in per_cell.values()])
    means = np.array([v.mean() for v in per_cell.values()])
    print(f"\ndrift in dW-bar over {len(rows)} baseline seeds, {len(POLICY_KEYS)} cells")
    print(f"  per-cell sd     median {np.median(sds):.4f}  "
          f"range [{sds.min():.4f}, {sds.max():.4f}]")
    print(f"  per-cell mean   median {np.median(means):+.4f}  "
          f"max |mean| {np.abs(means).max():.4f}   (should sit near zero)")

    # What a paired design could detect. The treatment-vs-A contrast is paired
    # on seed and shares its founding draws, so its noise is BELOW this; using
    # the unpaired baseline sd is therefore the conservative direction.
    print(f"\n  minimum detectable dW-bar shift (alpha .05, power .8, "
          f"conservative):")
    sd = float(np.median(sds))
    for n in (10, 20, 30, 50):
        print(f"    n={n:3d} paired seeds   {2.8 * sd / np.sqrt(n):+.4f}")

    dest = os.path.join(OUT, "drift_null.json")
    with open(dest, "w") as f:
        json.dump({"steps": steps, "n_seeds": len(rows),
                   "per_cell_sd": {k: float(v.std(ddof=1))
                                   for k, v in per_cell.items()},
                   "per_cell_mean": {k: float(v.mean())
                                     for k, v in per_cell.items()},
                   "median_sd": sd,
                   "mde": {n: 2.8 * sd / np.sqrt(n) for n in (10, 20, 30, 50)},
                   "rows": [{k: v for k, v in r.items() if k != "dW"}
                            for r in rows]}, f, indent=1)
    print(f"\nwrote {dest}")


# --- selection measured directly, not inferred from the population mean -----
# The horizon pilot found that this ecology coalesces to a SINGLE founder
# lineage (lineage_effective_n -> 1.0 in every run by 8000 steps). Change in
# the population mean W-bar is therefore dominated by one lineage's drift, and
# no run length fixes that -- longer runs coalesce harder, not less.
#
# The fix is to stop inferring selection from mean change and measure it
# directly. Robertson's secondary theorem / the Price equation give the
# selection differential on a trait z in one bout of reproduction as
#
#     S(z) = cov(z_i, n_i) / mean(n_i)
#
# with n_i realized lifetime offspring. This is valid in a single lineage,
# because it asks whether carrying a higher z was associated with leaving more
# offspring -- not whether the mean moved. And it comes with an exact null:
# under condition A no broadcast exists, so W has literally no effect on any
# agent's behaviour and the true selection differential on every cell is zero.
# Anything nonzero there is sampling noise, measured rather than assumed.

def selection_differential(sim, t0, t1):
    """S(z) per policy cell over agents whose whole life fits in [t0, t1], so
    offspring counts are final rather than censored."""
    cohort = [a for a in sim.agents.values()
              if a.policy and a.death_time is not None
              and a.birth_time >= t0 and a.death_time <= t1]
    if len(cohort) < 30:
        return None, len(cohort)
    n = np.array([a.offspring_count for a in cohort], float)
    nbar = n.mean()
    if nbar <= 0:
        return None, len(cohort)
    out = {}
    for k in POLICY_KEYS:
        z = np.array([a.policy[k] for a in cohort], float)
        out[k] = float(np.cov(z, n, bias=True)[0, 1] / nbar)
    return out, len(cohort)


def null_check(steps=4000, seeds=12):
    """Validate the instrument where the answer is known: under A, selection on
    W is exactly zero by construction."""
    os.makedirs(OUT, exist_ok=True)
    rows = []
    for seed in range(201, 201 + seeds):
        sim = Simulation(cfg_for(steps), seed=seed)
        sim.run()
        S, n = selection_differential(sim, 500, steps)
        if S is None:
            print(f"  seed {seed}: cohort too small ({n})")
            continue
        # A reference: selection on global_sensitivity, which under A is also
        # causally inert, and on a trait that genuinely matters (risk scales
        # harvest yield) as a positive control that the estimator can see
        # selection at all.
        cohort = [a for a in sim.agents.values()
                  if a.death_time is not None and a.birth_time >= 500
                  and a.death_time <= steps]
        nn = np.array([a.offspring_count for a in cohort], float)
        ref = {}
        for tr in ("global_sensitivity", "risk", "cooperation"):
            z = np.array([a.traits[tr] for a in cohort], float)
            ref[tr] = float(np.cov(z, nn, bias=True)[0, 1] / nn.mean())
        rows.append({"seed": seed, "cohort": n, "S": S, "traits": ref})
        print(f"  seed {seed}: cohort {n:4d}  |S|_med "
              f"{np.median(np.abs(list(S.values()))):.5f}  "
              f"S(risk) {ref['risk']:+.5f}  S(gamma) {ref['global_sensitivity']:+.5f}",
              flush=True)

    allS = np.array([[r["S"][k] for k in POLICY_KEYS] for r in rows])
    print(f"\npolicy cells, {len(rows)} baseline seeds x {len(POLICY_KEYS)} cells")
    print(f"  mean over seeds, per cell: median {np.median(allS.mean(0)):+.5f}, "
          f"max |mean| {np.abs(allS.mean(0)).max():.5f}   (expected ~0)")
    print(f"  sd over seeds, per cell:   median {np.median(allS.std(0, ddof=1)):.5f}")
    for tr in ("risk", "cooperation", "global_sensitivity"):
        v = np.array([r["traits"][tr] for r in rows])
        print(f"  S({tr:18s}) mean {v.mean():+.5f}  sd {v.std(ddof=1):.5f}")
    sd = float(np.median(allS.std(0, ddof=1)))
    print(f"\n  minimum detectable S (alpha .05, power .8):")
    for nn_ in (10, 20, 30, 50):
        print(f"    n={nn_:3d} paired seeds   {2.8 * sd / np.sqrt(nn_):+.5f}")
    dest = os.path.join(OUT, "selection_null.json")
    with open(dest, "w") as f:
        json.dump({"steps": steps, "n_seeds": len(rows),
                   "per_cell_mean": dict(zip(POLICY_KEYS, allS.mean(0).tolist())),
                   "per_cell_sd": dict(zip(POLICY_KEYS,
                                           allS.std(0, ddof=1).tolist())),
                   "trait_reference": {t: [r["traits"][t] for r in rows]
                                       for t in ("risk", "cooperation",
                                                 "global_sensitivity")},
                   "median_sd": sd}, f, indent=1)
    print(f"\nwrote {dest}")



if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--horizon", action="store_true")
    ap.add_argument("--null", action="store_true")
    ap.add_argument("--selection-null", action="store_true")
    ap.add_argument("--steps", type=int, default=None)
    a = ap.parse_args()
    if a.horizon:
        horizon()
    elif a.selection_null:
        null_check(a.steps or 4000)
    elif a.null:
        null(a.steps)
    else:
        ap.print_help()
