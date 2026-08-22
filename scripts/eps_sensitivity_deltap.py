#!/usr/bin/env python3
"""Does the passive-counterfactual conclusion depend on the epsilon threshold?

campaigns/reviewer_checks.json already shows RAW P is stable across
eps in {0.01, 0.02, 0.05}. The paper's conclusion, however, rests on Delta P =
P_actual - P_passive, so the sensitivity check has to be run on Delta P itself
-- writing "we repeated the Delta P calculation" on the strength of a raw-P
check would be an overclaim. Pure re-analysis of stored trajectories; no new
runs.
"""
import importlib.util, json, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
spec = importlib.util.spec_from_file_location(
    "pnc", os.path.join(HERE, "passive_null_checks.py"))
pnc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pnc)

KEYS, load, pull_series, actual_pull, paired = (
    pnc.KEYS, pnc.load, pnc.pull_series, pnc.actual_pull, pnc.paired)
harsh = os.path.join(ROOT, "campaigns", "harsh_shock", "runs")
replay = os.path.join(ROOT, "campaigns", "replay_control", "runs")
library = load(os.path.join(ROOT, "campaigns", "replay_control", "library.json"))
lib_keys = sorted(library)
seeds = list(range(1, 31))

out = {}
for eps in (0.01, 0.02, 0.05):
    pnc.EPS = eps          # module constant read inside pull_series/actual_pull
    dF, dR, dN = [], [], []
    for s in seeds:
        F = load(f"{harsh}/F_s{s}.json"); A = load(f"{harsh}/A_s{s}.json")
        N = load(f"{harsh}/N_s{s}.json"); B = load(f"{harsh}/B_s{s}.json")
        R = load(f"{replay}/R_s{s}.json")
        traj = library[lib_keys[(s - 1) % 15]]
        dF.append(actual_pull(F) - pull_series(
            A["globals"], lambda i, st: {k: 1.0 - st[k] for k in KEYS}))
        dR.append(actual_pull(R) - pull_series(
            B["globals"],
            lambda i, st, tr=traj: tr[min(i, len(tr) - 1)]))
        bl = N["broadcasts"]
        dN.append(actual_pull(N) - pull_series(
            A["globals"], lambda i, st, bl=bl: bl[i] if i < len(bl) else None))
    out[str(eps)] = {
        "delta_F_median": float(np.median(dF)),
        "delta_R_median": float(np.median(dR)),
        "delta_N_median": float(np.median(dN)),
        "F_all_negative_p": paired(dF, [0.0] * len(dF))["wilcoxon_p"],
        "R_all_negative_p": paired(dR, [0.0] * len(dR))["wilcoxon_p"],
        "N_all_negative_p": paired(dN, [0.0] * len(dN))["wilcoxon_p"],
        "diff_in_diff_F_vs_N_p": paired(dF, dN)["wilcoxon_p"],
        "diff_in_diff_R_vs_N_p": paired(dR, dN)["wilcoxon_p"],
    }
    o = out[str(eps)]
    print(f"eps={eps}:  dP medians  F {o['delta_F_median']:+.4f}  "
          f"R {o['delta_R_median']:+.4f}  N {o['delta_N_median']:+.4f}   "
          f"vs0 p: F {o['F_all_negative_p']:.1e} R {o['R_all_negative_p']:.1e} "
          f"N {o['N_all_negative_p']:.1e}   FvsN p {o['diff_in_diff_F_vs_N_p']:.3f}")

dest = os.path.join(ROOT, "campaigns", "eps_sensitivity_deltap.json")
with open(dest, "w") as f:
    json.dump(out, f, indent=1)
print("wrote", dest)
