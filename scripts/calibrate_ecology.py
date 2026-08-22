#!/usr/bin/env python3
"""Fit the model's ecology to an observed temporal network -- and prove first
that the fit works at all.

Step 10 of docs/PAPER2_PLAN.md says: calibrate ONE dataset end to end before
touching five, and if it cannot pass without loosening the threshold, ship the
simulation-only paper. This script is the machinery for that, plus the check
that has to come before any real data is trusted:

    --recover   generate a pseudo-dataset from KNOWN ecological parameters,
                run the fit against it, and ask whether the fit finds them.

If the fit cannot recover parameters it was itself given, no agreement it later
reports on real data means anything. This runs entirely offline.

DISCIPLINE, inherited from the ecology ensemble:
  * the fit sees condition A only -- never a broadcast condition;
  * the distance function, parameter box and candidate count are fixed here,
    before any dataset is loaded;
  * the simulated side is observed through scripts/temporal_observer.py, the
    SAME adapter used on real data. Comparing a simulator's internal S(t) to an
    adapter's view of real data would compare two different measurements: the
    internal view reports fragmentation 0.016 where the adapter reports 0.000
    on the identical run.

SCOPE, which belongs in the paper: the model is calibrated to INTENSIVE
macrostate quantities (rates, shares, Gini, mean degree), not to network size.
A 60-agent simulation is not made to be a 1,899-node messaging platform; it is
made to sit in the same region of macrostate space. Any claim beyond that is
not supported by this procedure.
"""
import argparse
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, HERE)
from project_one import Config, Simulation            # noqa: E402
import temporal_observer as TO                        # noqa: E402

OUT = os.path.join(ROOT, "campaigns", "calibration")

# --- fixed before any dataset is loaded ------------------------------------
PARAMS = ["resource_base_regen", "resource_capacity", "reproduce_cost",
          "metabolism", "action_cost", "max_lifespan_mean"]
BOX = 0.40                 # +/- fraction of default, wider than the ensemble's
N_CANDIDATES = 48
FIT_SEEDS = 2
STEPS = 4000
LHS_SEED = 20260821

# Intensive quantities only -- see SCOPE above. cooperation and turnover use
# the UNCAPPED rates (Sect. 3.3a, hazard 1): the observer's [0,1] clip is for
# broadcasting, and as a fit target it hides everything above the ceiling.
TARGETS = ("fragmentation", "centralization", "cooperation_raw",
           "inequality", "turnover_raw", "mean_degree")


def latin_hypercube(n, k, rng):
    """n points in [0,1]^k, one per stratum per dimension."""
    out = np.empty((n, k))
    for j in range(k):
        out[:, j] = (rng.permutation(n) + rng.random(n)) / n
    return out


def candidate_params(n=N_CANDIDATES, seed=LHS_SEED):
    base = Config()
    rng = np.random.RandomState(seed)
    u = latin_hypercube(n, len(PARAMS), rng)
    out = []
    for i in range(n):
        out.append({p: float(getattr(base, p) * (1.0 + BOX * (2 * u[i, j] - 1)))
                    for j, p in enumerate(PARAMS)})
    return out


def _interaction_stream(sim):
    """The dyadic acts an outside observer would actually record -- the
    simulated analogue of a messaging or contact log."""
    return [(str(e["agent"]), str(e["target"]), int(e["t"]))
            for e in sim.events
            if e["type"] in ("share", "connect") and "target" in e]


def observe_params(job):
    """Run condition A under one parameter set and return its target vector,
    measured through the same adapter that will read the real data."""
    params, seed, window = job
    cfg = Config(condition="A", steps=STEPS, shock_step=0, snapshot_interval=0)
    for k, v in params.items():
        setattr(cfg, k, v)
    sim = Simulation(cfg, seed=seed)
    sim.run()
    traj = TO.observe_stream(_interaction_stream(sim), window)
    if not traj:
        return None
    return [float(np.median([s[t] for s in traj if t in s])) for t in TARGETS]


def evaluate(param_sets, window, seeds=FIT_SEEDS, label="candidates"):
    jobs = [(p, s, window) for p in param_sets for s in range(1, seeds + 1)]
    workers = max(1, os.cpu_count() or 2)
    print(f"{label}: {len(jobs)} baseline runs on {workers} workers", flush=True)
    with ProcessPoolExecutor(max_workers=workers) as ex:
        res = list(ex.map(observe_params, jobs))
    out = []
    for i in range(len(param_sets)):
        block = [r for r in res[i * seeds:(i + 1) * seeds] if r is not None]
        out.append(np.median(np.array(block), axis=0) if block else None)
    return out


def fit(target_vec, cand_vecs, cand_params):
    """Normalized distance: each target z-scored by its spread ACROSS
    CANDIDATES, so no single statistic dominates because of its units. The
    scaling is derived from the candidate pool alone and never from the
    target, so it cannot be tuned to flatter a fit."""
    ok = [i for i, v in enumerate(cand_vecs) if v is not None]
    M = np.array([cand_vecs[i] for i in ok], float)
    sd = M.std(axis=0, ddof=1)
    sd[sd == 0] = 1.0
    d = np.linalg.norm((M - np.asarray(target_vec, float)) / sd, axis=1)
    order = np.argsort(d)
    return [{"rank": int(r), "candidate": int(ok[i]), "distance": float(d[i]),
             "params": cand_params[ok[i]], "targets": M[i].tolist()}
            for r, i in enumerate(order)], sd


def recover(window=5):
    """Can the fit find parameters it was given? Ground truth is a point well
    off centre, and the pseudo-dataset uses seeds the candidates never see."""
    os.makedirs(OUT, exist_ok=True)
    base = Config()
    truth = {p: float(getattr(base, p) * m) for p, m in zip(
        PARAMS, [1.30, 0.75, 1.25, 0.80, 1.35, 0.70])}
    print("ground truth (multiplier on default):")
    for p, m in zip(PARAMS, [1.30, 0.75, 1.25, 0.80, 1.35, 0.70]):
        print(f"  {p:22s} x{m:.2f}  = {truth[p]:.3f}")

    # the "dataset": same generator, unseen seeds
    tvecs = evaluate([truth], window, seeds=2, label="pseudo-dataset")
    if tvecs[0] is None:
        sys.exit("ground-truth run produced no observable windows")
    target = tvecs[0]
    print("\ntarget vector (what a real dataset would supply):")
    for t, v in zip(TARGETS, target):
        print(f"  {t:20s} {v:.4f}")

    cands = candidate_params()
    cvecs = evaluate(cands, window)
    ranked, sd = fit(target, cvecs, cands)

    print(f"\ndistance spread over {len(ranked)} candidates: "
          f"best {ranked[0]['distance']:.3f}, median "
          f"{np.median([r['distance'] for r in ranked]):.3f}, "
          f"worst {ranked[-1]['distance']:.3f}")
    if ranked[-1]["distance"] - ranked[0]["distance"] < 1e-6:
        print("  WARNING: the distance does not discriminate at all.")

    best = ranked[0]["params"]
    print(f"\n{'parameter':22s} {'truth':>10s} {'best fit':>10s} "
          f"{'error':>8s} {'|err| vs box':>13s}")
    errs = []
    for p in PARAMS:
        d = getattr(Config(), p)
        e = (best[p] - truth[p]) / d
        errs.append(abs(e))
        print(f"  {p:22s} {truth[p]:10.3f} {best[p]:10.3f} {e:+8.1%} "
              f"{abs(e) / BOX:13.2f}")

    # A random candidate is the null: does fitting beat picking one blindly?
    rnd = np.mean([[abs(c[p] - truth[p]) / getattr(Config(), p) for p in PARAMS]
                   for c in cands])
    print(f"\nmean |error| of the best fit : {np.mean(errs):.1%}")
    print(f"mean |error| of a random draw: {rnd:.1%}")
    verdict = np.mean(errs) < rnd
    print(f"\nfit beats a blind draw: {'YES' if verdict else 'NO'}")
    if not verdict:
        print("  -> the procedure does not identify the ecology. Do NOT run it\n"
              "     on real data; fix the targets or widen the horizon first.")

    dest = os.path.join(OUT, "recovery.json")
    with open(dest, "w") as f:
        json.dump({"truth": truth, "target_vector": dict(zip(TARGETS, target)),
                   "window": window, "box": BOX, "n_candidates": N_CANDIDATES,
                   "best": best, "mean_abs_error": float(np.mean(errs)),
                   "random_baseline": float(rnd), "identifies": bool(verdict),
                   "top": ranked[:5]}, f, indent=1)
    print(f"wrote {dest}")
    return 0 if verdict else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--recover", action="store_true",
                    help="validate the fit against known parameters (offline)")
    ap.add_argument("--window", type=int, default=5)
    a = ap.parse_args()
    if a.recover:
        sys.exit(recover(a.window))
    ap.print_help()
