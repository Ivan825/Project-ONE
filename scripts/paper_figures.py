#!/usr/bin/env python3
"""Regenerate the two figures used in the paper at their PRINTED size.

The campaign figures under campaigns/*/ are sized for on-screen reading
(7-11.5 inches wide). Dropped into a two-column-width LaTeX float at
~0.4-0.9\\textwidth they shrink by 3-4x and their tick labels become
unreadable. This script redraws the same data at close to final print size,
so a 7 pt label in the source is still ~6.5 pt on the page.

Outputs (written next to the campaign data AND into paper/figures/):
  paper_fig_sweep.png   -> Fig. 2, placed at 0.88\\textwidth
  paper_fig_trait.png   -> Fig. 3, placed at 0.46\\textwidth

Data sources are the same JSON the campaign figures use, so the numbers
cannot drift from the analysis.

    python scripts/paper_figures.py
"""
import json
import os
import statistics
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

GAINS = [0.2, 0.8, 1.6]
SWEEP = [f"{ROOT}/campaigns/sweep_g{g}" for g in ("0.2", "0.8", "1.6")]
HARSH = f"{ROOT}/campaigns/harsh_shock"

# Same palette / ordering as scripts/analyze_campaign.py
COLORS = {"A": "#8d8b85", "B": "#b3b0a8", "C": "#2f8f6f", "F": "#c2503a",
          "F:invert": "#c2503a", "F:crisis": "#e08a1e", "F:utopia": "#7a5cc4",
          "N": "#3a6fc2", "R": "#c23a94"}
LABELS = {"A": "no feedback", "B": "observed, blind", "C": "true",
          "F": "false (invert)", "F:invert": "lie: inverted",
          "F:crisis": "lie: crisis", "F:utopia": "lie: utopia",
          "N": "noise", "R": "replay"}
SWEEP_ORDER = ["A", "C", "F:invert", "F:crisis", "F:utopia", "N"]
SHORT_SWEEP = {"A": "none", "C": "true", "F:invert": "lie: invert",
               "F:crisis": "lie: crisis", "F:utopia": "lie: utopia",
               "N": "noise"}
BOX_ORDER = ["A", "B", "C", "F", "N"]

TITLE_FS, LABEL_FS, TICK_FS, LEG_FS = 7.8, 7.0, 6.4, 5.9


def _style(ax):
    ax.grid(axis="y", color="#e4e2dc", linewidth=0.6)
    ax.set_axisbelow(True)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    ax.tick_params(labelsize=TICK_FS, length=2.5, width=0.6)


def medians_by_cond(campaign_dir, key):
    with open(os.path.join(campaign_dir, "results.json")) as f:
        rows = json.load(f)["outcomes_per_run"]
    g = {}
    for r in rows:
        if r.get(key) is not None:
            g.setdefault(r["condition"], []).append(r[key])
    return {c: statistics.median(v) for c, v in g.items()}


def fig_sweep(dest):
    panels = [("trait_gs_delta", "Evolved attention",
               r"$\Delta$ mean $\gamma$"),
              ("fragmentation_post", "Fragmentation",
               "post-shock\nmean"),
              ("cooperation_rate", "Cooperation",
               "costly\nhelping p.c.")]
    series = {key: {c: [] for c in SWEEP_ORDER} for key, _, _ in panels}
    for d in SWEEP:
        for key, _, _ in panels:
            med = medians_by_cond(d, key)
            for c in SWEEP_ORDER:
                series[key][c].append(med.get(c))

    fig, axes = plt.subplots(1, 3, figsize=(4.45, 0.90), dpi=400)
    for ax, (key, title, ylab) in zip(axes, panels):
        # A and F:utopia coincide exactly (utopia triggers no corrective
        # response), so draw A wide underneath and utopia dashed on top --
        # otherwise one silently hides the other.
        for c in SWEEP_ORDER:
            y = series[key][c]
            if all(v is None for v in y):
                continue
            wide = c == "A"
            kw = dict(marker="o",
                      markersize=3.4 if wide else 2.4,
                      linewidth=2.4 if wide else 1.1,
                      alpha=0.55 if wide else 1.0,
                      color=COLORS[c], label=LABELS[c],
                      zorder=1 if wide else 2)
            if c == "F:utopia":
                kw["linestyle"] = (0, (2.6, 1.6))
            ax.plot(GAINS, y, **kw)
        ax.set_title(title, fontsize=TITLE_FS, loc="left", pad=3)
        ax.set_xlabel("feedback gain", fontsize=LABEL_FS, labelpad=1.5)
        ax.set_ylabel(ylab, fontsize=LABEL_FS, labelpad=1.5)
        ax.set_xticks(GAINS)
        _style(ax)
    # One shared legend above the panels: inside any panel it would sit on top
    # of the data (every panel is full).
    h, _ = axes[0].get_legend_handles_labels()
    fig.legend(h, [SHORT_SWEEP[c] for c in SWEEP_ORDER], ncol=6,
               loc="upper center", bbox_to_anchor=(0.5, 1.13),
               fontsize=LEG_FS, frameon=False, handlelength=1.3,
               columnspacing=1.1, handletextpad=0.4)
    fig.tight_layout(pad=0.35, w_pad=0.9, rect=(0, 0, 1, 0.86))
    fig.savefig(dest, bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)
    print(f"wrote {dest}")


def fig_trait(dest):
    with open(os.path.join(HARSH, "results.json")) as f:
        rows = json.load(f)["outcomes_per_run"]
    g = {}
    for r in rows:
        if r.get("trait_gs_delta") is not None:
            g.setdefault(r["condition"], []).append(r["trait_gs_delta"])
    conds = [c for c in BOX_ORDER if g.get(c)]
    data = [g[c] for c in conds]

    fig, ax = plt.subplots(figsize=(2.75, 1.30), dpi=400)
    bp = ax.boxplot(data, patch_artist=True, widths=0.55,
                    medianprops=dict(color="#0b0b0b", linewidth=1.0),
                    boxprops=dict(linewidth=0.7),
                    whiskerprops=dict(linewidth=0.7),
                    capprops=dict(linewidth=0.7),
                    flierprops=dict(marker="o", markersize=1.6, alpha=0.5))
    for patch, c in zip(bp["boxes"], conds):
        patch.set_facecolor(COLORS[c])
        patch.set_alpha(0.75)
        patch.set_edgecolor("#52514e")
    short = {"A": "none", "B": "blind", "C": "true", "F": "lie", "N": "noise"}
    ax.set_xticklabels([short.get(c, LABELS[c]) for c in conds],
                       fontsize=TICK_FS + 0.6)
    ax.set_ylabel(r"$\Delta$ mean $\gamma$", fontsize=LABEL_FS, labelpad=1.5)
    ax.axhline(0, color="#9a978f", linewidth=0.6, linestyle=":")
    _style(ax)
    fig.tight_layout(pad=0.3)
    fig.savefig(dest, bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)
    print(f"wrote {dest}")


def main():
    outdir = os.path.join(ROOT, "paper", "figures")
    os.makedirs(outdir, exist_ok=True)
    fig_sweep(os.path.join(outdir, "paper_fig_sweep.png"))
    fig_trait(os.path.join(outdir, "paper_fig_trait.png"))


if __name__ == "__main__":
    main()
