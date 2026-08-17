#!/usr/bin/env python3
"""Cross-sweep summary figure: how the core effects scale with feedback gain.

    python scripts/sweep_figure.py campaigns/sweep_g0.2 campaigns/sweep_g0.8 \
        campaigns/sweep_g1.6 -o campaigns/sweep_summary.png
"""
import argparse
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

COLOR = {"C": "#1baf7a", "F:invert": "#eda100", "F:crisis": "#e34948",
         "F:utopia": "#8a8880", "N": "#e87ba4", "A": "#2a78d6"}
LABEL = {"C": "true", "F:invert": "lie: inverted", "F:crisis": "lie: crisis",
         "F:utopia": "lie: utopia", "N": "noise", "A": "no feedback"}


def med(vals):
    v = sorted(vals)
    return v[len(v) // 2] if v else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dirs", nargs="+")
    ap.add_argument("-o", "--out", default="campaigns/sweep_summary.png")
    args = ap.parse_args()

    data = {}  # token -> gain -> {outcome: median}
    gains = []
    for d in args.dirs:
        res = json.load(open(f"{d}/results.json"))
        gain = json.load(open(f"{d}/manifest.json"))["feedback_gain"]
        gains.append(gain)
        rows = {}
        for r in res["outcomes_per_run"]:
            rows.setdefault(r["condition"], []).append(r)
        for tok, rs in rows.items():
            for key in ("story_pull", "trait_gs_delta", "cooperation_rate"):
                vals = [r[key] for r in rs if r[key] is not None]
                if vals:
                    data.setdefault(tok, {}).setdefault(gain, {})[key] = med(vals)

    panels = [("trait_gs_delta", "Evolved change in attention to the self-model",
               "Δ mean global_sensitivity"),
              ("story_pull", "Pull of the macrostate toward the broadcast",
               "signed movement per tick"),
              ("cooperation_rate", "Cooperation rate", "costly helping per capita")]
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.0), dpi=150)
    for ax, (key, title, ylab) in zip(axes, panels):
        for tok in ("A", "C", "F:invert", "F:crisis", "F:utopia", "N"):
            if tok not in data:
                continue
            xs = sorted(g for g in data[tok] if key in data[tok][g])
            ys = [data[tok][g][key] for g in xs]
            if not xs:
                continue
            ax.plot(xs, ys, marker="o", markersize=5, linewidth=1.8,
                    color=COLOR[tok], label=LABEL[tok])
        ax.axhline(0, color="#8a8880", linewidth=0.8, linestyle=":")
        ax.set_title(title, fontsize=10, loc="left")
        ax.set_xlabel("feedback gain", fontsize=9)
        ax.set_ylabel(ylab, fontsize=9)
        ax.grid(color="#e4e2dc", linewidth=0.6)
        ax.set_axisbelow(True)
        for sp in ("top", "right"):
            ax.spines[sp].set_visible(False)
    axes[0].legend(fontsize=7.5, frameon=False)
    fig.suptitle("Sensitivity sweep: 40% hub-removal shock, 20 seeds per cell",
                 fontsize=10, x=0.01, ha="left", color="#52514e")
    fig.tight_layout()
    fig.savefig(args.out)
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
