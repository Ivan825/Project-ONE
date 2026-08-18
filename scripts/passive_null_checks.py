#!/usr/bin/env python3
"""Passive-counterfactual nulls for the story-pull statistic (Eq. 2).

The story-pull statistic could in principle be inflated by intrinsic dynamics
that move the macrostate toward the reference signal even when nothing is
broadcast (e.g., regression toward 0.5 under the inverted reference). These
checks evaluate Eq. 2 on trajectories that NEVER received the signal:

1. Passive-invert null: for each harsh-shock baseline trajectory (condition A,
   which logs S(t) but broadcasts nothing), construct the counterfactual
   reference b*(t) = 1 - S_A(t) post hoc and evaluate Eq. 2. Compare paired
   (by seed) against the actual F:invert runs.
2. Passive-replay null: for each replay receiver seed s (source j=(s-1)%15),
   evaluate Eq. 2 on the matched observed-but-blind harsh trajectory B_s
   against the SAME replay reference trajectory, post hoc. Compare paired
   against the actual R runs.
3. Shock-transition exclusion: recompute R (and F, N) story pull after
   deleting the observer transition that spans the standardized shock.

All checks are pure re-analysis of stored trajectories; no new simulations.
Writes campaigns/passive_null_checks.json.

    python scripts/passive_null_checks.py
"""
import json
import os

import numpy as np
from scipy.stats import wilcoxon, rankdata

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
KEYS = ["fragmentation", "centralization", "cooperation", "inequality", "turnover"]
EPS = 0.02
RS = np.random.RandomState(0)
N_BOOT = 10000


def load(path):
    with open(path) as f:
        return json.load(f)


def pull_series(globals_list, ref_fn, skip_shock_t=None):
    """Eq. 2 with reference signal ref_fn(i, state) per observer tick.

    skip_shock_t: if set, drop the transition whose LEFT endpoint has t equal
    to the shock step (the observer tick at which the shock is applied).
    """
    g = globals_list
    moves = []
    for i in range(len(g) - 1):
        if skip_shock_t is not None and g[i]["t"] == skip_shock_t:
            continue
        b = ref_fn(i, g[i])
        if b is None:
            continue
        for k in KEYS:
            gap = b[k] - g[i][k]
            if abs(gap) > EPS:
                step = g[i + 1][k] - g[i][k]
                moves.append(step if gap > 0 else -step)
    return sum(moves) / len(moves) if moves else None


def actual_pull(run, skip_shock_t=None):
    bl = run["broadcasts"]
    return pull_series(run["globals"],
                       lambda i, s: bl[i] if i < len(bl) else None,
                       skip_shock_t)


def paired(a, b):
    d = np.asarray(a) - np.asarray(b)
    nz = d[d != 0]
    stat, p = wilcoxon(nz)
    ranks = rankdata(np.abs(nz), method="average")
    rb = float((ranks[nz > 0].sum() - ranks[nz < 0].sum()) / ranks.sum())
    boots = [np.median(d[RS.randint(0, len(d), len(d))]) for _ in range(N_BOOT)]
    lo, hi = np.percentile(boots, [2.5, 97.5])
    return {"n": int(len(d)), "median_diff": float(np.median(d)),
            "mean_diff": float(np.mean(d)), "wilcoxon_p": float(p),
            "rank_biserial": rb, "boot_ci_median": [float(lo), float(hi)]}


def main():
    harsh = os.path.join(ROOT, "campaigns", "harsh_shock", "runs")
    replay = os.path.join(ROOT, "campaigns", "replay_control", "runs")
    library = load(os.path.join(ROOT, "campaigns", "replay_control", "library.json"))
    seeds = list(range(1, 31))
    out = {}

    # ---- 1. passive-invert null on A trajectories
    pF, pPassive = [], []
    for s in seeds:
        F = load(f"{harsh}/F_s{s}.json")
        A = load(f"{harsh}/A_s{s}.json")
        pF.append(actual_pull(F))
        pPassive.append(pull_series(
            A["globals"], lambda i, st: {k: 1.0 - st[k] for k in KEYS}))
    out["passive_invert"] = {
        "P_F_median": float(np.median(pF)),
        "P_passive_median": float(np.median(pPassive)),
        "F_minus_passive": paired(pF, pPassive),
    }

    # ---- 2. passive-replay null on matched B trajectories
    lib_keys = sorted(library)  # same assignment rule as replay_control.py
    pR, pRpassive = [], []
    for s in seeds:
        R = load(f"{replay}/R_s{s}.json")
        B = load(f"{harsh}/B_s{s}.json")
        traj = library[lib_keys[(s - 1) % 15]]  # per-tick broadcast dicts
        def ref(i, st, traj=traj):
            idx = min(i, len(traj) - 1)
            return traj[idx]
        pR.append(actual_pull(R))
        pRpassive.append(pull_series(B["globals"], ref))
    out["passive_replay"] = {
        "P_R_median": float(np.median(pR)),
        "P_passiveR_median": float(np.median(pRpassive)),
        "R_minus_passive": paired(pR, pRpassive),
    }

    # ---- 2b. passive-noise null + per-condition causal deltas
    # Score each no-feedback trajectory A_s against the noise reference the
    # matched N_s run actually received; the causal steering effect of a
    # broadcast is then Delta = P_actual - P_passive with matched reference.
    if os.path.exists(f"{harsh}/N_s1.json"):
        pN, pNpassive = [], []
        for s in seeds:
            N = load(f"{harsh}/N_s{s}.json")
            A = load(f"{harsh}/A_s{s}.json")
            bl = N["broadcasts"]
            pN.append(actual_pull(N))
            pNpassive.append(pull_series(
                A["globals"], lambda i, st, bl=bl: bl[i] if i < len(bl) else None))
        dF = [a - b for a, b in zip(pF, pPassive)]
        dR = [a - b for a, b in zip(pR, pRpassive)]
        dN = [a - b for a, b in zip(pN, pNpassive)]
        out["passive_noise"] = {
            "P_N_median": float(np.median(pN)),
            "P_passiveN_median": float(np.median(pNpassive)),
            "N_minus_passive": paired(pN, pNpassive),
        }
        out["causal_deltas"] = {
            "delta_F_median": float(np.median(dF)),
            "delta_R_median": float(np.median(dR)),
            "delta_N_median": float(np.median(dN)),
            "diff_in_diff_F_vs_N": paired(dF, dN),
            "diff_in_diff_R_vs_N": paired(dR, dN),
            "diff_in_diff_R_vs_F": paired(dR, dF),
        }

    # ---- 2c. per-component actual vs passive (F, harsh) for mechanism clarity
    comp = {}
    for s in seeds:
        F = load(f"{harsh}/F_s{s}.json")
        A = load(f"{harsh}/A_s{s}.json")
        for name, g, ref in (
                ("actual_F", F["globals"],
                 lambda i, st, bl=F["broadcasts"]: bl[i] if i < len(bl) else None),
                ("passive_A", A["globals"],
                 lambda i, st: {k: 1.0 - st[k] for k in KEYS})):
            per = {}
            for i in range(len(g) - 1):
                b = ref(i, g[i])
                if b is None:
                    continue
                for k in KEYS:
                    gap = b[k] - g[i][k]
                    if abs(gap) > EPS:
                        step = g[i + 1][k] - g[i][k]
                        per.setdefault(k, []).append(step if gap > 0 else -step)
            for k, mv in per.items():
                comp.setdefault(name, {}).setdefault(k, []).append(
                    sum(mv) / len(mv))
    out["per_component"] = {
        name: {k: float(np.median(v)) for k, v in ks.items()}
        for name, ks in comp.items()}

    # ---- 3. shock-transition exclusion (drop t=2000 -> t=2010 transition)
    excl = {}
    for cond, base in (("R", f"{replay}/R_s%d.json"),
                       ("F", f"{harsh}/F_s%d.json"),
                       ("N", f"{harsh}/N_s%d.json")):
        if not os.path.exists(base % seeds[0]):
            continue
        full = [actual_pull(load(base % s)) for s in seeds]
        cut = [actual_pull(load(base % s), skip_shock_t=2000) for s in seeds]
        excl[cond] = {"median_full": float(np.median(full)),
                      "median_excl_shock_transition": float(np.median(cut))}
    out["shock_transition_exclusion"] = excl

    dest = os.path.join(ROOT, "campaigns", "passive_null_checks.json")
    with open(dest, "w") as f:
        json.dump(out, f, indent=1)
    print(json.dumps(out, indent=1))
    print(f"\nwrote {dest}")


if __name__ == "__main__":
    main()
