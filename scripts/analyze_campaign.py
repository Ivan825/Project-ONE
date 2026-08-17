#!/usr/bin/env python3
"""Pre-registered analysis of a flagship campaign.

    python scripts/analyze_campaign.py campaigns/flagship

Primary outcomes (frozen in docs/PLAN.md before the campaign):
  1. recovery_time_90     - steps after the shock until living population first
                            returns to 90% of its pre-shock mean (censored at
                            horizon if it never does).
  2. fragmentation_post   - mean fragmentation over the post-shock window.
  3. cooperation_rate     - mean cooperation over the post-transient window.
  4. self_model_convergence - mean per-tick reduction in |actual - broadcast|
                            across broadcast keys; positive = the world drifts
                            TOWARD the story it is told (self-fulfilling),
                            negative = away (self-defeating). Defined only for
                            broadcasting conditions (C, F, N).

Statistics: Mann-Whitney U vs. baseline A (and F vs C for convergence),
Cliff's delta effect sizes. Figures follow the repo's palette.
"""
import argparse
import glob
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.stats import mannwhitneyu

BROADCAST_KEYS = ("fragmentation", "centralization", "cooperation",
                  "inequality", "turnover")
COND_ORDER = ["A", "B", "C", "F", "N"]
COND_COLOR = {"A": "#2a78d6", "B": "#eb6834", "C": "#1baf7a",
              "F": "#eda100", "N": "#e87ba4"}
COND_LABEL = {"A": "A local only", "B": "B observed blind", "C": "C true feedback",
              "F": "F false feedback", "N": "N noise feedback"}
TRANSIENT = 500


def outcomes(run):
    g = run["globals"]
    ts = [s["t"] for s in g]
    pop = [s["population"] for s in g]
    shock = run["shock_step"]
    horizon = run["steps"]

    pre = [p for s, p in zip(g, pop) if shock - 500 <= s["t"] < shock]
    baseline = sum(pre) / len(pre) if pre else 0.0
    rec = horizon - shock  # censored default
    censored = True
    for s, p in zip(g, pop):
        if s["t"] > shock and baseline > 0 and p >= 0.9 * baseline:
            rec, censored = s["t"] - shock, False
            break

    frag_post = [s["fragmentation"] for s in g if s["t"] > shock]
    coop = [s["cooperation"] for s in g if s["t"] >= TRANSIENT]

    conv = None
    bl = run.get("broadcasts") or []
    if any(b is not None for b in bl):
        deltas = []
        for i in range(len(g) - 1):
            b = bl[i] if i < len(bl) else None
            if b is None:
                continue
            for k in BROADCAST_KEYS:
                d_now = abs(g[i][k] - b[k])
                d_next = abs(g[i + 1][k] - b[k])
                deltas.append(d_now - d_next)
        conv = sum(deltas) / len(deltas) if deltas else None

    return {
        "condition": run["condition"], "seed": run["seed"],
        "recovery_time_90": rec, "recovery_censored": censored,
        "fragmentation_post": sum(frag_post) / len(frag_post) if frag_post else None,
        "cooperation_rate": sum(coop) / len(coop) if coop else None,
        "self_model_convergence": conv,
        "final_population": run["final_population"],
    }


def cliffs_delta(a, b):
    gt = sum(1 for x in a for y in b if x > y)
    lt = sum(1 for x in a for y in b if x < y)
    return (gt - lt) / (len(a) * len(b)) if a and b else 0.0


def compare(name, groups, ref="A"):
    out = {}
    base = groups.get(ref, [])
    for cond, vals in groups.items():
        if cond == ref or not vals or not base:
            continue
        u, p = mannwhitneyu(vals, base, alternative="two-sided")
        out[f"{cond}_vs_{ref}"] = {
            "n": (len(vals), len(base)),
            "median": (_med(vals), _med(base)),
            "p_value": float(p), "cliffs_delta": cliffs_delta(vals, base),
        }
    return out


def _med(v):
    s = sorted(v)
    n = len(s)
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


def boxfig(path, groups, title, ylabel):
    fig, ax = plt.subplots(figsize=(7, 4.2), dpi=150)
    conds = [c for c in COND_ORDER if c in groups and groups[c]]
    data = [groups[c] for c in conds]
    bp = ax.boxplot(data, patch_artist=True, widths=0.55,
                    medianprops=dict(color="#0b0b0b", linewidth=1.6),
                    flierprops=dict(marker="o", markersize=3, alpha=0.5))
    for patch, c in zip(bp["boxes"], conds):
        patch.set_facecolor(COND_COLOR[c])
        patch.set_alpha(0.75)
        patch.set_edgecolor("#52514e")
    ax.set_xticklabels([COND_LABEL[c] for c in conds], fontsize=8.5)
    ax.set_title(title, fontsize=11, loc="left")
    ax.set_ylabel(ylabel, fontsize=9.5)
    ax.grid(axis="y", color="#e4e2dc", linewidth=0.7)
    ax.set_axisbelow(True)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def trajfig(path, runs_by_cond, key, title, ylabel, shock):
    fig, ax = plt.subplots(figsize=(8, 4.2), dpi=150)
    for cond in COND_ORDER:
        runs = runs_by_cond.get(cond)
        if not runs:
            continue
        ts = [s["t"] for s in runs[0]["globals"]]
        n = min(len(r["globals"]) for r in runs)
        mean = [sum(r["globals"][i][key] for r in runs) / len(runs)
                for i in range(n)]
        ax.plot(ts[:n], mean, color=COND_COLOR[cond], linewidth=1.8,
                label=COND_LABEL[cond])
    ax.axvline(shock, color="#52514e", linestyle="--", linewidth=1, alpha=0.7)
    ax.text(shock, ax.get_ylim()[1], " shock", fontsize=8, color="#52514e",
            va="top")
    ax.set_title(title, fontsize=11, loc="left")
    ax.set_xlabel("t", fontsize=9.5)
    ax.set_ylabel(ylabel, fontsize=9.5)
    ax.legend(fontsize=8, frameon=False, ncol=2)
    ax.grid(color="#e4e2dc", linewidth=0.7)
    ax.set_axisbelow(True)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("campaign_dir")
    args = ap.parse_args()
    d = args.campaign_dir

    runs = [json.load(open(p)) for p in
            sorted(glob.glob(os.path.join(d, "runs", "*.json")))]
    if not runs:
        raise SystemExit("no runs found")
    rows = [outcomes(r) for r in runs]
    runs_by_cond = {}
    for r in runs:
        runs_by_cond.setdefault(r["condition"], []).append(r)

    def grp(key, conds=None):
        g = {}
        for row in rows:
            if row[key] is None:
                continue
            if conds and row["condition"] not in conds:
                continue
            g.setdefault(row["condition"], []).append(row[key])
        return g

    shock = runs[0]["shock_step"]
    results = {
        "n_runs": len(runs),
        "recovery_time_90": compare("recovery", grp("recovery_time_90")),
        "fragmentation_post": compare("frag", grp("fragmentation_post")),
        "cooperation_rate": compare("coop", grp("cooperation_rate")),
        "self_model_convergence": {
            **compare("conv", grp("self_model_convergence"), ref="N"),
            "medians": {c: _med(v) for c, v in
                        grp("self_model_convergence").items()},
        },
        "final_population_medians": {c: _med(v) for c, v in
                                     grp("final_population").items()},
    }
    with open(os.path.join(d, "results.json"), "w") as f:
        json.dump({"outcomes_per_run": rows, "statistics": results}, f, indent=2)

    boxfig(os.path.join(d, "fig1_recovery.png"), grp("recovery_time_90"),
           "Recovery time after shock (population to 90% of pre-shock mean)",
           "steps (censored at horizon)")
    boxfig(os.path.join(d, "fig2_fragmentation.png"), grp("fragmentation_post"),
           "Post-shock fragmentation (mean)", "fragmentation")
    boxfig(os.path.join(d, "fig3_cooperation.png"), grp("cooperation_rate"),
           "Cooperation rate (post-transient mean)", "costly helping per capita")
    boxfig(os.path.join(d, "fig4_convergence.png"),
           grp("self_model_convergence", conds={"C", "F", "N"}),
           "Drift toward the broadcast self-model (+ = self-fulfilling)",
           "mean per-tick reduction in |actual − broadcast|")
    trajfig(os.path.join(d, "fig5_population.png"), runs_by_cond, "population",
            "Mean population trajectory by condition", "living agents", shock)
    trajfig(os.path.join(d, "fig6_cooperation_traj.png"), runs_by_cond,
            "cooperation", "Mean cooperation trajectory by condition",
            "cooperation rate", shock)

    print(json.dumps(results, indent=2))
    print(f"\nwrote results.json and 6 figures to {d}/")


if __name__ == "__main__":
    main()
