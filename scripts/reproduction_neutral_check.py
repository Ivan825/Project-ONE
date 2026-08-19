#!/usr/bin/env python3
"""Architectural robustness controls for the evolutionary-attention result.

Two independent controls, each rerunning the full 15-cell gain sweep
(5 broadcast conditions x 3 gains x 20 paired seeds = 300 runs each):

  A. reproduction_neutral -- removes the reproductive-opportunity channel
     (campaigns/rn_g*), see below.
  B. pruning_gamma_free   -- fixes the hub-targeted pruning probability at 0.5
     for every agent (campaigns/pgf_g*), removing gamma's influence on
     target selection while preserving the mechanism and consuming the
     identical RNG draw. Addresses the asymmetry that pruning-target
     selection scales with gamma_i while action propensities scale with
     gamma_i * g.

Control A in detail:

Feedback adds weight only to non-reproductive actions (connect/share/harvest/
prune). After normalization this mechanically lowers P(reproduce) for
higher-gamma agents whenever the broadcast carries corrective drive:

    P(reproduce | gamma, b) = w_r / (W_0 + gamma * g * D(b)),
    d/d(gamma) < 0  whenever D(b) > 0,

with D(b) = sum_a f_a(b). Since the intensity predictor I = g*<D(b)> is
precisely the quantity controlling that penalty, the observed gamma decline
could in principle be a direct reproductive-opportunity cost rather than
ecological selection.

Config flag `reproduction_neutral=True` rescales the reproduce weight by
(1 + D_i/N_0), leaving P(reproduce) exactly at its no-broadcast value while
preserving the intended feedback effect on every other action. This script
compares the standard gain sweep against the reproduction-neutral rerun
(5 broadcast conditions x 3 gains x 20 paired seeds).

Writes campaigns/reproduction_neutral_check.json.

    python scripts/reproduction_neutral_check.py
"""
import json
import os

import numpy as np
from scipy.stats import spearmanr, wilcoxon

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
KEYS = ["fragmentation", "centralization", "cooperation", "inequality", "turnover"]
CONDS = ["C", "F:invert", "F:crisis", "F:utopia", "N"]
GAINS = ["0.2", "0.8", "1.6"]
VARIANT = os.environ.get("PO_VARIANT", "rn")   # "rn" or "pgf"
PREFIX = {"rn": "rn_g", "pgf": "pgf_g"}[VARIANT]
OUTNAME = {"rn": "reproduction_neutral_check.json",
           "pgf": "pruning_gamma_free_check.json"}[VARIANT]


def drive(b):
    return (max(0.0, b["fragmentation"] - 0.3)
            + max(0.0, 0.5 - b["cooperation"])
            + 0.5 * max(0.0, b["inequality"] - 0.5)
            + max(0.0, b["turnover"] - 0.5)
            + 0.3 * max(0.0, b["centralization"] - 0.6))


def load(path):
    with open(path) as f:
        return json.load(f)


def dgamma(run):
    g = run["globals"]
    a = next((x.get("mean_trait_global_sensitivity") for x in g
              if "mean_trait_global_sensitivity" in x), None)
    b = next((x.get("mean_trait_global_sensitivity") for x in reversed(g)
              if "mean_trait_global_sensitivity" in x), None)
    return (b - a) if (a is not None and b is not None) else None


def intensity(run, gain):
    ds = [drive(b) for b in run["broadcasts"] if b is not None]
    return gain * float(np.mean(ds)) if ds else 0.0


def main():
    out = {"cells": {}, "paired_tests": {}, "variant": VARIANT}
    cell_I, cell_dg_std, cell_dg_neu = [], [], []

    for gain in GAINS:
        for cond in CONDS:
            tok = cond.replace(":", "-")
            std, neu, Is = [], [], []
            for s in range(1, 21):
                p_std = f"{ROOT}/campaigns/sweep_g{gain}/runs/{tok}_s{s}.json"
                p_neu = f"{ROOT}/campaigns/{PREFIX}{gain}/runs/{tok}_s{s}.json"
                if not (os.path.exists(p_std) and os.path.exists(p_neu)):
                    continue
                r_std, r_neu = load(p_std), load(p_neu)
                std.append(dgamma(r_std))
                neu.append(dgamma(r_neu))
                Is.append(intensity(r_neu, float(gain)))
            if len(neu) < 10:
                continue
            key = f"{cond}@g{gain}"
            ms, mn = float(np.median(std)), float(np.median(neu))
            d = np.asarray(neu) - np.asarray(std)
            if np.allclose(d, 0):
                p = 1.0
            else:
                nz = d[d != 0]
                p = float(wilcoxon(nz)[1])
            out["cells"][key] = {
                "n": len(neu), "I": float(np.median(Is)),
                "dgamma_standard": ms, "dgamma_control": mn,
                "retained_fraction": (mn / ms) if abs(ms) > 1e-9 else None,
                "paired_shift_p": p,
            }
            cell_I.append(float(np.median(Is)))
            cell_dg_std.append(ms)
            cell_dg_neu.append(mn)

    rs, ps = spearmanr(cell_I, cell_dg_std)
    rn, pn = spearmanr(cell_I, cell_dg_neu)
    out["intensity_correlation"] = {
        "n_cells": len(cell_I),
        "standard_rho": float(rs),
        "control_rho": float(rn),
    }
    # Overall retention across the conditions that actually decline
    decl = [(v["dgamma_standard"], v["dgamma_control"])
            for v in out["cells"].values() if v["dgamma_standard"] < -0.05]
    out["overall"] = {
        "n_declining_cells": len(decl),
        "median_retained_fraction": float(np.median([b / a for a, b in decl])),
        "sum_standard": float(sum(a for a, _ in decl)),
        "sum_control": float(sum(b for _, b in decl)),
    }

    dest = f"{ROOT}/campaigns/{OUTNAME}"
    with open(dest, "w") as f:
        json.dump(out, f, indent=1)

    print(f"{'cell':18s} {'I':>6s} {'std':>8s} {'neutral':>9s} {'retained':>9s}")
    for k, v in out["cells"].items():
        rt = "n/a" if v["retained_fraction"] is None else f"{100*v['retained_fraction']:.0f}%"
        print(f"{k:18s} {v['I']:6.2f} {v['dgamma_standard']:8.3f} "
              f"{v['dgamma_control']:9.3f} {rt:>9s}")
    print(f"\nSpearman(I, dgamma): standard {rs:.3f} | reproduction-neutral {rn:.3f}")
    print(f"median retention across declining cells: "
          f"{100*out['overall']['median_retained_fraction']:.0f}%")
    print(f"wrote {dest}")


if __name__ == "__main__":
    main()
