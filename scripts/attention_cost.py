#!/usr/bin/env python3
"""Continuous predictor of the evolved attention decline.

For every broadcast-condition run in the gain sweep, compute:
  E = mean broadcast-state discrepancy <|b_k - s_k|>  (credibility)
  I = g * mean total corrective drive <sum_a f_a(b)>
      (BROADCAST-IMPLIED corrective-drive intensity)
and relate them to the evolved change in mean global sensitivity (dgamma).

Note on interpretation: I is computed from the broadcast alone and
deliberately OMITS the per-agent factor gamma_i, which is the very quantity
under selection; it is therefore the drive a broadcast implies, not the
realized per-agent behavioral perturbation. I is also computed from realized
(already feedback-affected) trajectories rather than independently
randomized. The relationship below is descriptive, not a causal mediation
result.

Result (15 sweep cells): dgamma tracks I almost perfectly (cell-level
Spearman rho ~ -0.99; run-level ~ -0.83, n=300), which parsimoniously
organizes the categorical ordering: utopia (I=0) shows no decline, truth
(E=0, small I) declines only at high gain, and unreliable high-drive
broadcasts decline most.

Writes campaigns/attention_cost.json.

    python scripts/attention_cost.py
"""
import json
import os

import numpy as np
from scipy.stats import spearmanr

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
KEYS = ["fragmentation", "centralization", "cooperation", "inequality", "turnover"]
CELLS = [("sweep_g0.2", 0.2), ("sweep_g0.8", 0.8), ("sweep_g1.6", 1.6)]
CONDS = ["C", "F:invert", "F:crisis", "F:utopia", "N"]


def fa_sum(b):
    """Total corrective response drive sum_a f_a(b) (engine constants)."""
    return (max(0.0, b["fragmentation"] - 0.3)
            + max(0.0, 0.5 - b["cooperation"])
            + 0.5 * max(0.0, b["inequality"] - 0.5)
            + max(0.0, b["turnover"] - 0.5)
            + 0.3 * max(0.0, b["centralization"] - 0.6))


def main():
    rows = []
    for camp, g in CELLS:
        res = json.load(open(f"{ROOT}/campaigns/{camp}/results.json"))
        gs = {(r["condition"], r["seed"]): r["trait_gs_delta"]
              for r in res["outcomes_per_run"]}
        for cond in CONDS:
            for s in range(1, 21):
                f = (f"{ROOT}/campaigns/{camp}/runs/"
                     f"{cond.replace(':', '-')}_s{s}.json")
                if not os.path.exists(f):
                    continue
                run = json.load(open(f))
                E, D = [], []
                for gl, b in zip(run["globals"], run["broadcasts"]):
                    if b is None:
                        continue
                    E.append(np.mean([abs(b[k] - gl[k]) for k in KEYS]))
                    D.append(fa_sum(b))
                rows.append({"cell": f"{cond}@g{g}", "condition": cond,
                             "gain": g, "E": float(np.mean(E)),
                             "I": float(g * np.mean(D)),
                             "dgamma": gs.get((cond, s))})

    cells = {}
    for r in rows:
        cells.setdefault(r["cell"], []).append(r)
    cell_stats = {c: {"E": float(np.median([x["E"] for x in v])),
                      "I": float(np.median([x["I"] for x in v])),
                      "dgamma": float(np.median([x["dgamma"] for x in v]))}
                  for c, v in sorted(cells.items())}
    E = np.array([v["E"] for v in cell_stats.values()])
    I = np.array([v["I"] for v in cell_stats.values()])
    d = np.array([v["dgamma"] for v in cell_stats.values()])
    rI, pI = spearmanr(I, d)
    rE, pE = spearmanr(E, d)
    rEI, pEI = spearmanr(E * I, d)
    rr = np.array([r["I"] for r in rows]), np.array([r["dgamma"] for r in rows])
    rIr, pIr = spearmanr(*rr)
    out = {"cells": cell_stats,
           "spearman_cell_level": {"dgamma_vs_I": [float(rI), float(pI)],
                                   "dgamma_vs_E": [float(rE), float(pE)],
                                   "dgamma_vs_ExI": [float(rEI), float(pEI)]},
           "spearman_run_level_dgamma_vs_I": [float(rIr), float(pIr)],
           "n_runs": len(rows)}
    dest = f"{ROOT}/campaigns/attention_cost.json"
    with open(dest, "w") as f:
        json.dump(out, f, indent=1)
    print(json.dumps(out["spearman_cell_level"], indent=1))
    print(f"wrote {dest}")


if __name__ == "__main__":
    main()
