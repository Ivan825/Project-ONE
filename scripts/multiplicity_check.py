#!/usr/bin/env python3
"""Multiplicity check for the paper's confirmatory contrasts (Table 3).

The design reports many paired contrasts across several campaigns, so a
reviewer is entitled to ask whether any reported significance survives
correction for multiple comparisons. This script does the check rather than
arguing about it.

The confirmatory family is the eight numerical contrasts in Table 3. (The two
non-numerical rows carry no p-value: the B-vs-A row is an exact identity --
every per-seed difference is 0 -- and the recovery-time row summarises a set
of nulls whose smallest p is reported as a bound.)

Two corrections are applied, from opposite ends of the strictness range:

  Benjamini-Hochberg  controls the false discovery rate -- the conventional
                      choice for a family of this size.
  Holm-Bonferroni     controls the family-wise error rate -- strictly more
                      conservative; if a decision survives Holm it survives
                      essentially any correction a reviewer would propose.

p-values are recomputed from the stored run records rather than copied from
the paper, so the check cannot inherit a transcription error. (The two
adjusted story-pull rows are the exception: they are read from
passive_null_checks.json, the derived artifact that defines them.)

A second, deliberately hostile family is also reported. Scoping a correction
to the table that needs it invites the objection that the family was chosen
to make the result come out, so the same two corrections are applied to a
superset containing every paired contrast reported anywhere in the paper --
including all 30 architectural-control cells. Writes
campaigns/multiplicity_check.json.

    python scripts/multiplicity_check.py
"""
import json
import os
import sys

import numpy as np
from scipy.stats import wilcoxon

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ALPHA = 0.05

# (label, campaign, outcome key, condition, reference)  -- Table 3 order.
# story-pull rows are handled separately: they come from the passive-null JSON.
TABLE3 = [
    ("story pull, raw (HS) F vs N",  "harsh_shock", "story_pull",         "F", "N"),
    ("cooperation (FL) C vs A",      "flagship",    "cooperation_rate",   "C", "A"),
    ("cooperation (HS) C vs A",      "harsh_shock", "cooperation_rate",   "C", "A"),
    ("fragmentation (FL) F vs A",    "flagship",    "fragmentation_post", "F", "A"),
    ("dgamma (HS) F vs A",           "harsh_shock", "trait_gs_delta",     "F", "A"),
    ("dgamma (HS) N vs A",           "harsh_shock", "trait_gs_delta",     "N", "A"),
]


def paired_p(campaign, key, cond, ref):
    """Recompute the paper's primary statistic: Wilcoxon signed-rank on
    per-seed differences, zeros dropped (as scipy's default does)."""
    path = f"{ROOT}/campaigns/{campaign}/results.json"
    with open(path) as f:
        rows = json.load(f)["outcomes_per_run"]
    by = {}
    for r in rows:
        if r.get(key) is not None:
            by.setdefault(r["condition"], {})[r["seed"]] = r[key]
    a, b = by.get(ref, {}), by.get(cond, {})
    seeds = sorted(set(a) & set(b))
    d = np.array([b[s] - a[s] for s in seeds], dtype=float)
    if np.allclose(d, 0):
        return 1.0, len(seeds)
    nz = d[d != 0]
    return float(wilcoxon(nz, alternative="two-sided")[1]), len(seeds)


def benjamini_hochberg(ps, alpha=ALPHA):
    """Return per-hypothesis reject decisions under BH step-up."""
    m = len(ps)
    order = np.argsort(ps)
    reject = np.zeros(m, dtype=bool)
    kmax = 0
    for i, idx in enumerate(order, start=1):
        if ps[idx] <= alpha * i / m:
            kmax = i
    for i, idx in enumerate(order, start=1):
        if i <= kmax:
            reject[idx] = True
    return reject


def holm_bonferroni(ps, alpha=ALPHA):
    """Return per-hypothesis reject decisions under Holm step-down."""
    m = len(ps)
    order = np.argsort(ps)
    reject = np.zeros(m, dtype=bool)
    for i, idx in enumerate(order, start=1):
        if ps[idx] <= alpha / (m - i + 1):
            reject[idx] = True
        else:
            break
    return reject


def wider_family():
    """Every other paired contrast reported anywhere in the paper, so the
    Table 3 decisions can be re-checked inside a family nobody could accuse
    of being drawn to flatter them."""
    extra = []

    # Per-condition Delta-P vs its own passive twin, plus the R-vs-N contrast.
    with open(f"{ROOT}/campaigns/passive_null_checks.json") as f:
        pn = json.load(f)
    for lab, node in [
        ("dP vs passive (F)", pn["passive_invert"]["F_minus_passive"]),
        ("dP vs passive (R)", pn["passive_replay"]["R_minus_passive"]),
        ("dP vs passive (N)", pn["passive_noise"]["N_minus_passive"]),
        ("story pull, adj. (HS) R vs N",
         pn["causal_deltas"]["diff_in_diff_R_vs_N"]),
        ("story pull, adj. (HS) R vs F",
         pn["causal_deltas"]["diff_in_diff_R_vs_F"]),
    ]:
        extra.append((lab, float(node["wilcoxon_p"]), int(node["n"])))

    # Recovery-time nulls collapsed behind the "> 0.22" bound in Table 3,
    # and every outcome reported for the 2x scale check.
    for camp, conds in [("flagship", ["C", "F", "N"]),
                        ("harsh_shock", ["C", "F", "N"]),
                        ("size2x", ["C", "F:invert", "N"])]:
        for cond in conds:
            p_, n_ = paired_p(camp, "recovery_time_90", cond, "A")
            extra.append((f"recovery ({camp}) {cond} vs A", p_, n_))
    for cond in ["C", "F:invert", "N"]:
        for key, tag in [("cooperation_rate", "cooperation"),
                         ("trait_gs_delta", "dgamma")]:
            p_, n_ = paired_p("size2x", key, cond, "A")
            extra.append((f"{tag} (2x) {cond} vs A", p_, n_))

    # All 30 architectural-control cells (control vs standard, per sweep cell).
    for variant, fname in [("rn", "reproduction_neutral_check.json"),
                           ("pgf", "pruning_gamma_free_check.json")]:
        with open(f"{ROOT}/campaigns/{fname}") as f:
            cells = json.load(f)["cells"]
        for cell, v in cells.items():
            extra.append((f"{variant} shift {cell}",
                          float(v["paired_shift_p"]), int(v["n"])))
    return extra


def summarise(labels, ps, ns):
    ps = np.asarray(ps, dtype=float)
    raw, bh, holm = ps <= ALPHA, benjamini_hochberg(ps), holm_bonferroni(ps)
    rows = [{"contrast": labels[i], "n_pairs": ns[i], "p": float(ps[i]),
             "sig_uncorrected": bool(raw[i]), "sig_bh": bool(bh[i]),
             "sig_holm": bool(holm[i])} for i in np.argsort(ps)]
    return raw, bh, holm, rows


def main():
    labels, ps, ns = [], [], []

    for label, camp, key, cond, ref in TABLE3:
        p, n = paired_p(camp, key, cond, ref)
        labels.append(label)
        ps.append(p)
        ns.append(n)

    # The two adjusted story-pull contrasts live in the passive-null output.
    with open(f"{ROOT}/campaigns/passive_null_checks.json") as f:
        pn = json.load(f)
    for label, node in [
        ("story pull, adj. (HS) F vs N",
         pn["causal_deltas"]["diff_in_diff_F_vs_N"]),
        ("story pull, adj. (FL) F vs N",
         pn["flagship"]["diff_in_diff_F_vs_N"]),
    ]:
        labels.append(label)
        ps.append(float(node["wilcoxon_p"]))
        ns.append(int(node["n"]))

    raw, bh, holm, rows = summarise(labels, ps, ns)

    # Same eight decisions, re-checked inside the hostile superset.
    ex = wider_family()
    w_labels = labels + [e[0] for e in ex]
    w_ps = list(ps) + [e[1] for e in ex]
    w_ns = ns + [e[2] for e in ex]
    w_raw, w_bh, w_holm, w_rows = summarise(w_labels, w_ps, w_ns)
    k = len(labels)
    wide_ok_bh = bool((w_bh[:k] == raw[:k]).all())
    wide_ok_holm = bool((w_holm[:k] == raw[:k]).all())
    # Contrasts OUTSIDE Table 3 that the enlarged family does demote.
    demoted = [w_labels[i] for i in range(k, len(w_ps))
               if w_raw[i] and not (w_bh[i] and w_holm[i])]

    out = {
        "alpha": ALPHA,
        "family": "the eight point-p contrasts of Table 3",
        "m": int(len(ps)),
        "contrasts": rows,
        "n_significant_uncorrected": int(raw.sum()),
        "n_significant_bh": int(bh.sum()),
        "n_significant_holm": int(holm.sum()),
        "bh_changes_no_decision": bool((bh == raw).all()),
        "holm_changes_no_decision": bool((holm == raw).all()),
        "wider_family": {
            "m": int(len(w_ps)),
            "description": "every paired contrast reported anywhere in the "
                           "paper, incl. all 30 architectural-control cells",
            "table3_decisions_unchanged_bh": wide_ok_bh,
            "table3_decisions_unchanged_holm": wide_ok_holm,
            "demoted_outside_table3": demoted,
            "contrasts": w_rows,
        },
    }

    dest = f"{ROOT}/campaigns/multiplicity_check.json"
    with open(dest, "w") as f:
        json.dump(out, f, indent=1)

    print(f"family: m = {out['m']} contrasts, alpha = {ALPHA}\n")
    print(f"{'contrast':32s} {'n':>3s} {'p':>11s}  raw   BH  Holm")
    for r in rows:
        print(f"{r['contrast']:32s} {r['n_pairs']:3d} {r['p']:11.3g}  "
              f"{'Y' if r['sig_uncorrected'] else '.':^3s}  "
              f"{'Y' if r['sig_bh'] else '.':^3s}  "
              f"{'Y' if r['sig_holm'] else '.':^4s}")
    print(f"\nsignificant: uncorrected {out['n_significant_uncorrected']}, "
          f"BH {out['n_significant_bh']}, Holm {out['n_significant_holm']}")
    print(f"BH changes no decision:   {out['bh_changes_no_decision']}")
    print(f"Holm changes no decision: {out['holm_changes_no_decision']}")
    w = out["wider_family"]
    print(f"\nenlarged family (m = {w['m']}): Table 3 decisions unchanged "
          f"under BH {w['table3_decisions_unchanged_bh']}, "
          f"Holm {w['table3_decisions_unchanged_holm']}")
    if w["demoted_outside_table3"]:
        print("  demoted OUTSIDE Table 3 (paper must not lean on these):")
        for d in w["demoted_outside_table3"]:
            print(f"    - {d}")
    print(f"wrote {dest}")

    if not out["bh_changes_no_decision"]:
        print("\n*** BH FLIPS AT LEAST ONE DECISION -- the paper must say so ***")
        sys.exit(1)


if __name__ == "__main__":
    main()
