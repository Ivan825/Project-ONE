#!/usr/bin/env python3
"""Stored-run analyses answering three reviewer questions (docs/REVIEW_QA.md).

All three are pure re-analysis of trajectories and run records already in
campaigns/ -- no new simulations, and the manuscript is not touched. The
pre-specified outcomes of the paper are unchanged; everything here is labeled
exploratory and lives in the repository / rebuttal material.

  Q1  Delta-P under the CONFORMIST regime: the conformist campaign (15 paired
      seeds, harsh shock) stores full globals + broadcasts, so the passive-twin
      construction of scripts/passive_null_checks.py applies verbatim. We
      import that module and reuse its Eq.-2 machinery so both regimes are
      scored by the same code path.

  Q5  Alternative resilience metrics on the corrective harsh-shock campaign:
      area-under-recovery-curve (population), fragmentation recovery time,
      and post-shock cooperation stability. The pre-specified metric remains
      recovery-time-to-90%; these are exploratory and uncorrected.

  Q3  Lineage-level evidence for the realized gamma shift: per-run
      Robertson/Price selection differentials S(gamma) and final
      lineage_effective_n from the 150 stored fixed-mode runs.

Writes campaigns/review_response_checks.json.

    python scripts/review_response_checks.py
"""
import json
import os
import sys

import numpy as np
from scipy.stats import wilcoxon

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import passive_null_checks as PNC  # noqa: E402  (same Eq.-2 code path)


def load(path):
    with open(path) as f:
        return json.load(f)


def med(x):
    return float(np.median(x))


# --------------------------------------------------------------------------
# Q1: Delta-P under the conformist regime (15 paired seeds, harsh shock)
# --------------------------------------------------------------------------
def q1_conformist_deltap():
    runs = os.path.join(ROOT, "campaigns", "conformist", "runs")
    seeds = list(range(1, 16))
    pF, pFpass, pN, pNpass = [], [], [], []
    for s in seeds:
        F = load(f"{runs}/F-invert_s{s}.json")
        N = load(f"{runs}/N_s{s}.json")
        A = load(f"{runs}/A_s{s}.json")
        # actual story pull under the broadcast each run received
        pF.append(PNC.actual_pull(F))
        pN.append(PNC.actual_pull(N))
        # passive twins: the SAME references scored on the never-fed A twin
        pFpass.append(PNC.pull_series(
            A["globals"], lambda i, st: {k: 1.0 - st[k] for k in PNC.KEYS}))
        bl = N["broadcasts"]
        pNpass.append(PNC.pull_series(
            A["globals"], lambda i, st, bl=bl: bl[i] if i < len(bl) else None))
    dF = [a - b for a, b in zip(pF, pFpass)]
    dN = [a - b for a, b in zip(pN, pNpass)]
    return {
        "design": "conformist response_mode, harsh shock, 15 paired seeds; "
                  "passive twins constructed exactly as in "
                  "passive_null_checks.py (same imported code)",
        "P_F_median": med(pF), "P_F_passive_median": med(pFpass),
        "F_minus_passive": PNC.paired(pF, pFpass),
        "P_N_median": med(pN), "P_N_passive_median": med(pNpass),
        "N_minus_passive": PNC.paired(pN, pNpass),
        "delta_F_median": med(dF), "delta_N_median": med(dN),
        "diff_in_diff_F_vs_N": PNC.paired(dF, dN),
    }


# --------------------------------------------------------------------------
# Q5: alternative resilience metrics (corrective harsh shock, 30 paired seeds)
# --------------------------------------------------------------------------
def _resilience_metrics(run):
    g = run["globals"]
    shock = run["shock_step"]
    pre = [x for x in g if 1000 <= x["t"] < shock]     # post-transient window
    post = [x for x in g if x["t"] >= shock]
    if not pre or not post:
        return None
    pop0 = np.mean([x["population"] for x in pre])
    frag0 = np.mean([x["fragmentation"] for x in pre])
    # 1. area-under-recovery-curve: mean post-shock population relative to the
    #    pre-shock baseline, capped at 1 (overshoot is not extra resilience)
    auc = np.mean([min(x["population"] / pop0, 1.0) for x in post])
    # 2. fragmentation recovery time: first post-shock tick at which
    #    fragmentation returns within 0.05 of its pre-shock mean, censored at
    #    the horizon if it never does
    t_rec = run["steps"]
    for x in post:
        if x["fragmentation"] <= frag0 + 0.05:
            t_rec = x["t"] - shock
            break
    coop_post = [x["cooperation"] for x in post]
    return {"auc_recovery": float(auc),
            "frag_recovery_time": float(t_rec),
            "coop_post_mean": float(np.mean(coop_post)),
            "coop_post_sd": float(np.std(coop_post, ddof=1))}


def q5_alt_resilience():
    runs = os.path.join(ROOT, "campaigns", "harsh_shock", "runs")
    seeds = list(range(1, 31))
    conds = ["A", "B", "C", "F", "N"]
    vals = {c: {} for c in conds}
    for c in conds:
        per = [_resilience_metrics(load(f"{runs}/{c}_s{s}.json"))
               for s in seeds]
        for k in per[0]:
            vals[c][k] = [p[k] for p in per]
    out = {"design": "corrective harsh-shock campaign, 30 paired seeds; "
                     "exploratory alternatives to the pre-specified "
                     "recovery-time-to-90% metric; p-values raw/uncorrected",
           "medians": {c: {k: med(v) for k, v in vals[c].items()}
                       for c in conds},
           "contrasts": {}}
    for k in ("auc_recovery", "frag_recovery_time",
              "coop_post_mean", "coop_post_sd"):
        for a, b in (("F", "A"), ("F", "N")):
            d = np.asarray(vals[a][k]) - np.asarray(vals[b][k])
            nz = d[d != 0]
            if len(nz) < 5:
                res = {"n_nonzero": int(len(nz)), "note": "too few nonzero"}
            else:
                stat, p = wilcoxon(nz)
                res = {"median_diff": med(d), "wilcoxon_p": float(p),
                       "n_nonzero": int(len(nz))}
            out["contrasts"][f"{k}:{a}_vs_{b}"] = res
    return out


# --------------------------------------------------------------------------
# Q3: stored lineage-level evidence for the realized gamma shift
# --------------------------------------------------------------------------
def q3_selection_differentials():
    camp = os.path.join(ROOT, "campaigns", "policy_campaign")
    fixed = [r for r in (json.loads(l)
                         for l in open(f"{camp}/runs_device.jsonl"))
             if r.get("mode") == "fixed"]
    # lineage_effective_n was recorded from the evolved-mode campaign onward;
    # the fixed-mode device runs predate the field (all None there). The
    # coalescence evidence therefore comes from the evolved runs and is
    # labeled as such -- do not attribute it to the fixed regime.
    evolved = [r for r in (json.loads(l) for l in open(f"{camp}/runs.jsonl"))
               if r.get("mode") == "evolved"
               and r.get("lineage_effective_n") is not None]
    out = {"design": "S(gamma)=cov(gamma,n)/n-bar over completed lifetimes "
                     "(Robertson/Price) from the 150 fixed-mode runs "
                     "(30 paired seeds x A/B/C/F/N, the manuscript's regime); "
                     "lineage_effective_n (inverse Simpson over founder lines, "
                     "final observer tick) from the 150 evolved-mode runs, "
                     "where the field was recorded",
           "S_gamma_fixed_mode": {}, "lineage_evolved_mode": {}}
    for cond in ("A", "B", "C", "F", "N"):
        sub = [r for r in fixed if r["cond"] == cond]
        sg = np.array([r["S_traits"]["global_sensitivity"] for r in sub])
        dg = np.array([r["trait_gs_delta"] for r in sub])
        nz = sg[sg != 0]
        stat, p = wilcoxon(nz) if len(nz) >= 5 else (None, None)
        out["S_gamma_fixed_mode"][cond] = {
            "n": len(sub),
            "S_gamma_median": med(sg),
            "S_gamma_iqr": [float(np.percentile(sg, 25)),
                            float(np.percentile(sg, 75))],
            "S_gamma_frac_negative": float(np.mean(sg < 0)),
            "S_gamma_wilcoxon_p_vs_0": float(p) if p is not None else None,
            "realized_dgamma_median": med(dg),
        }
        esub = [r for r in evolved if r["cond"] == cond]
        if esub:
            ln = np.array([r["lineage_effective_n"] for r in esub])
            out["lineage_evolved_mode"][cond] = {
                "n": len(esub),
                "lineage_effective_n_median": med(ln),
                "frac_coalesced_to_single_line":
                    float(np.mean(ln <= 1.0 + 1e-9)),
                "frac_at_most_two_lines": float(np.mean(ln <= 2.0)),
            }
    return out


def main():
    out = {"q1_conformist_deltap": q1_conformist_deltap(),
           "q5_alternative_resilience": q5_alt_resilience(),
           "q3_selection_differentials": q3_selection_differentials()}
    dest = os.path.join(ROOT, "campaigns", "review_response_checks.json")
    with open(dest, "w") as f:
        json.dump(out, f, indent=1)
    print(json.dumps(out, indent=1))
    print(f"\nwrote {dest}")


if __name__ == "__main__":
    main()
