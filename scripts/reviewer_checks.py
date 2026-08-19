#!/usr/bin/env python3
"""Reviewer-requested robustness analyses, all from stored campaign data.

1. Replay source-dependence: R vs F / R vs N restricted to one receiver per
   source trajectory (seeds 1-15 map 1:1 onto the 15 library sources), plus a
   source-clustered bootstrap on the full n=30.
2. Direct test that story pull > 0 for F:invert and R (bootstrap CI of the
   mean vs zero + one-sample Wilcoxon).
3. Epsilon sensitivity of story pull (eps in {0.01, 0.02, 0.05}), recomputed
   from stored per-tick globals/broadcasts.
4. Response-activation control: mean |b-s| discrepancy and per-threshold
   activation fractions for R / F / N (and C for reference).

Writes campaigns/reviewer_checks.json.

    python scripts/reviewer_checks.py
"""
import json
import os
import sys

import numpy as np
from scipy.stats import rankdata, wilcoxon

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
KEYS = ["fragmentation", "centralization", "cooperation", "inequality", "turnover"]
RS = np.random.RandomState(0)
N_BOOT = 10000


def load_run(path):
    with open(path) as f:
        return json.load(f)


def story_pull(run, eps):
    g, bl = run["globals"], run["broadcasts"]
    moves = []
    for i in range(len(g) - 1):
        b = bl[i] if i < len(bl) else None
        if b is None:
            continue
        for k in KEYS:
            gap = b[k] - g[i][k]
            if abs(gap) > eps:
                step = g[i + 1][k] - g[i][k]
                moves.append(step if gap > 0 else -step)
    return sum(moves) / len(moves) if moves else None


def discrepancy_stats(run):
    """Mean |b-s| and fraction of observer ticks each corrective rule fires."""
    g, bl = run["globals"], run["broadcasts"]
    diffs, n = [], 0
    thr = {"frag>0.3": 0, "coop<0.5": 0, "ineq>0.5": 0, "turn>0.5": 0, "cent>0.6": 0}
    for i in range(len(g)):
        b = bl[i] if i < len(bl) else None
        if b is None:
            continue
        n += 1
        diffs.extend(abs(b[k] - g[i][k]) for k in KEYS)
        thr["frag>0.3"] += b["fragmentation"] > 0.3
        thr["coop<0.5"] += b["cooperation"] < 0.5
        thr["ineq>0.5"] += b["inequality"] > 0.5
        thr["turn>0.5"] += b["turnover"] > 0.5
        thr["cent>0.6"] += b["centralization"] > 0.6
    return (float(np.mean(diffs)) if diffs else None,
            {k: v / n for k, v in thr.items()} if n else {})


def paired(a, b):
    """a, b aligned per-seed arrays -> paired Wilcoxon + rank-biserial + CI."""
    d = np.asarray(a) - np.asarray(b)
    if np.all(d == 0):
        return {"n": len(d), "note": "all per-seed differences exactly zero"}
    nz = d[d != 0]
    stat, p = wilcoxon(nz)
    n = len(d)
    # signed, tie-corrected matched-pairs rank-biserial (same form as
    # scripts/analyze_campaign.py); the 1-4W/n(n+1) shortcut loses the sign.
    ranks = rankdata(np.abs(nz), method="average")
    r = float((ranks[nz > 0].sum() - ranks[nz < 0].sum()) / ranks.sum())
    boots = [np.mean(d[RS.randint(0, n, n)]) for _ in range(N_BOOT)]
    lo, hi = np.percentile(boots, [2.5, 97.5])
    return {"n": n, "median_diff": float(np.median(d)), "mean_diff": float(np.mean(d)),
            "wilcoxon_p": float(p), "rank_biserial_r": float(r),
            "boot_ci_mean": [float(lo), float(hi)]}


def cluster_boot(diff, cluster_ids):
    """Bootstrap resampling CLUSTERS (source trajectories), CI of mean diff."""
    diff = np.asarray(diff)
    ids = np.asarray(cluster_ids)
    uniq = np.unique(ids)
    means = []
    for _ in range(N_BOOT):
        pick = uniq[RS.randint(0, len(uniq), len(uniq))]
        sel = np.concatenate([diff[ids == c] for c in pick])
        means.append(sel.mean())
    lo, hi = np.percentile(means, [2.5, 97.5])
    return {"n_clusters": int(len(uniq)), "mean_diff": float(diff.mean()),
            "cluster_boot_ci": [float(lo), float(hi)]}


def one_sample(vals):
    v = np.asarray([x for x in vals if x is not None])
    stat, p = wilcoxon(v)
    idx = [RS.randint(0, len(v), len(v)) for _ in range(N_BOOT)]
    boots_mean = [np.mean(v[i]) for i in idx]
    boots_med = [np.median(v[i]) for i in idx]
    lo, hi = np.percentile(boots_mean, [2.5, 97.5])
    mlo, mhi = np.percentile(boots_med, [2.5, 97.5])
    return {"n": len(v), "mean": float(v.mean()), "median": float(np.median(v)),
            "wilcoxon_p_vs_zero": float(p),
            "boot_ci_mean": [float(lo), float(hi)],
            "boot_ci_median": [float(mlo), float(mhi)]}


def main():
    out = {}
    harsh = os.path.join(ROOT, "campaigns", "harsh_shock", "runs")
    replay = os.path.join(ROOT, "campaigns", "replay_control", "runs")

    # ---- load per-seed story pull (eps=0.02) for R, F:invert, N, seeds 1..30
    pull = {"R": {}, "F": {}, "N": {}}
    runs_cache = {}
    for s in range(1, 31):
        for cond, path in (("R", f"{replay}/R_s{s}.json"),
                           ("F", f"{harsh}/F_s{s}.json"),
                           ("N", f"{harsh}/N_s{s}.json")):
            run = load_run(path)
            runs_cache[(cond, s)] = run
            pull[cond][s] = story_pull(run, 0.02)

    # ---- 1. source-dependence
    seeds15 = list(range(1, 16))
    seeds30 = list(range(1, 31))
    out["replay_source_dependence"] = {
        "subset_one_receiver_per_source": {
            "R_vs_F": paired([pull["R"][s] for s in seeds15],
                             [pull["F"][s] for s in seeds15]),
            "R_vs_N": paired([pull["R"][s] for s in seeds15],
                             [pull["N"][s] for s in seeds15]),
        },
        "full_n30_source_clustered_bootstrap": {
            "R_vs_F": cluster_boot([pull["R"][s] - pull["F"][s] for s in seeds30],
                                   [(s - 1) % 15 for s in seeds30]),
            "R_vs_N": cluster_boot([pull["R"][s] - pull["N"][s] for s in seeds30],
                                   [(s - 1) % 15 for s in seeds30]),
        },
    }

    # ---- 2. story pull > 0 directly
    out["pull_gt_zero"] = {
        "F_invert_harsh": one_sample(list(pull["F"].values())),
        "R_replay": one_sample(list(pull["R"].values())),
        "N_noise_harsh": one_sample(list(pull["N"].values())),
    }

    # ---- 3. epsilon sensitivity (same runs, eps grid)
    eps_out = {}
    for eps in (0.01, 0.02, 0.05):
        row = {}
        for cond in ("R", "F", "N"):
            vals = [story_pull(runs_cache[(cond, s)], eps) for s in seeds30]
            vals = [v for v in vals if v is not None]
            row[cond] = {"median": float(np.median(vals)), "mean": float(np.mean(vals))}
        d_FN = [story_pull(runs_cache[("F", s)], eps) - story_pull(runs_cache[("N", s)], eps)
                for s in seeds30]
        row["F_vs_N_paired"] = paired(d_FN, [0] * len(d_FN))
        eps_out[str(eps)] = row
    out["epsilon_sensitivity"] = eps_out

    # ---- 4. response-activation control (add C from harsh for reference)
    act = {}
    for cond in ("R", "F", "N"):
        ds, th = [], []
        for s in seeds30:
            d, t = discrepancy_stats(runs_cache[(cond, s)])
            ds.append(d)
            th.append(t)
        act[cond] = {"mean_abs_discrepancy": float(np.mean(ds)),
                     "activation_fractions": {k: float(np.mean([t[k] for t in th]))
                                              for k in th[0]}}
    ds, th = [], []
    for s in seeds30:
        d, t = discrepancy_stats(load_run(f"{harsh}/C_s{s}.json"))
        ds.append(d)
        th.append(t)
    act["C"] = {"mean_abs_discrepancy": float(np.mean(ds)),
                "activation_fractions": {k: float(np.mean([t[k] for t in th]))
                                         for k in th[0]}}
    out["response_activation"] = act

    dest = os.path.join(ROOT, "campaigns", "reviewer_checks.json")
    with open(dest, "w") as f:
        json.dump(out, f, indent=1)
    print(json.dumps(out, indent=1))
    print(f"\nwrote {dest}")


if __name__ == "__main__":
    main()
