#!/usr/bin/env python3
"""Prepare everything for a live demonstration in one command.

    python scripts/demo.py

Creates demo/ containing:
  - paired A-vs-F runs (same seed) with dashboards, ready to open side by side
  - a fresh replay-check transcript proving determinism
  - copies of the campaign report, findings, and key figures
  - DEMO.md: the step-by-step run sheet with every command and talking point
"""
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
DEMO = os.path.join(ROOT, "demo")
PY = sys.executable


def sh(args, capture=False):
    print("  $", " ".join(args))
    if capture:
        r = subprocess.run(args, cwd=ROOT, capture_output=True, text=True)
        return r.stdout + r.stderr
    subprocess.run(args, cwd=ROOT, check=True)
    return ""


def main():
    os.makedirs(DEMO, exist_ok=True)

    print("[1/5] Paired runs: same seed, with and without the false mirror")
    for cond, extra, name in [
        ("A", [], "world_A_no_feedback"),
        ("F", ["--distortion", "invert"], "world_F_false_feedback"),
    ]:
        out = os.path.join(DEMO, name)
        sh([PY, "run.py", "--condition", cond, *extra,
            "--steps", "2000", "--seed", "7", "--out", out])
        sh([PY, "scripts/dashboard.py", out])

    print("[2/5] Determinism transcript")
    transcript = sh([PY, "scripts/replay_check.py"], capture=True)
    with open(os.path.join(DEMO, "replay_check_output.txt"), "w") as f:
        f.write(transcript)
    print(transcript.strip().splitlines()[-1])

    print("[3/5] Copying campaign evidence")
    copies = [
        ("campaigns/flagship/report.html", "campaign_report.html"),
        ("campaigns/FINDINGS.md", "FINDINGS.md"),
        ("campaigns/sweep_summary.png", "fig_sweep_summary.png"),
        ("campaigns/harsh_shock/fig8_trait_evolution.png",
         "fig_trait_evolution.png"),
        ("campaigns/harsh_shock/fig7_story_pull.png", "fig_story_pull.png"),
    ]
    for src, dst in copies:
        s = os.path.join(ROOT, src)
        if os.path.exists(s):
            shutil.copy(s, os.path.join(DEMO, dst))
        else:
            print(f"  (skipped missing {src})")

    print("[4/5] Extracting the side-by-side numbers")
    import json
    lines = ["Same seed (7), t=2000, only the broadcast differs:", ""]
    for name, label in [("world_A_no_feedback", "A  (no feedback)   "),
                        ("world_F_false_feedback", "F  (false feedback)")]:
        gpath = os.path.join(DEMO, name, "global_states.jsonl")
        with open(gpath) as f:
            last = json.loads(f.readlines()[-1])
        lines.append(
            f"{label}: population={last['population']}  "
            f"mean_degree={last['mean_degree']:.1f}  "
            f"cooperation={last['cooperation']:.2f}  "
            f"fragmentation={last['fragmentation']:.3f}")
    comparison = "\n".join(lines)
    with open(os.path.join(DEMO, "side_by_side.txt"), "w") as f:
        f.write(comparison + "\n")
    print("  " + "\n  ".join(lines))

    print("[5/5] Writing the run sheet")
    with open(os.path.join(DEMO, "DEMO.md"), "w") as f:
        f.write(RUNSHEET.replace("__COMPARISON__", comparison))

    print(f"\nDemo ready in {DEMO}/ — open DEMO.md for the run sheet.")


RUNSHEET = """# Demo run sheet (~20 minutes)

Everything below is pre-generated in this folder; live commands are optional
theatre. Rehearse once the night before.

## 1. The living world (3 min)
Open `world_F_false_feedback/dashboard.html` in a browser.
Press Play. Point out: births, deaths, rewiring, the timelines.
Click a node: traits, ancestry, cause of death.
> "Every agent is a transparent six-number trait vector. No neural nets --
> every behaviour is inspectable."

## 2. Determinism (2 min)
Live in a terminal (or show `replay_check_output.txt`):

    python scripts/replay_check.py

> "Identical state hashes on every re-run -- and the same hashes on this Mac
> and a Linux cloud machine. Every figure in the paper regenerates from a
> config and a seed."

## 3. The core experiment, same seed (5 min)
Pre-generated here; to run live:

    python run.py --condition A --steps 2000 --seed 7 --out demo/world_A_no_feedback
    python run.py --condition F --distortion invert --steps 2000 --seed 7 --out demo/world_F_false_feedback

Open both dashboards side by side. Then show `side_by_side.txt`:

__COMPARISON__

> "Same world, same randomness. One is simply lied to about itself.
> The lie roughly doubles connectivity and raises costly helping --
> information alone did that."

## 4. Evidence at scale (5 min)
Open `campaign_report.html`.
Walk: (a) B vs A tiles -- measurement alone is causally inert, delta = 0.000;
(b) story-pull distributions -- note these are the RAW statistic, whose
apparent steering is explained away by the passive counterfactual;
(c) trajectories -- toggle conditions in the legend.
Then open `fig_trait_evolution.png`:
> "Attention to the broadcast is a heritable trait, and under consequential
> broadcasts its population mean declines. Nobody programmed that ordering,
> and it survives a control holding reproductive opportunity invariant."

## 5. Robustness and the honest null (3 min)
Open `fig_sweep_summary.png`: dose-response across feedback gains; the three
lie types (exploitative / mobilizing / inert). Mention the null: recovery
time is feedback-insensitive even at 40% hub removal -- reported as such.
Close:
> "927 runs, pre-specified outcome families, one repo, two commands to reproduce
> any figure. What I want from you is criticism: what's the weakest part?"

Then stop talking and let him drive.

## Backup checklist (night before)
- [ ] `python scripts/demo.py` re-run cleanly
- [ ] Both dashboards open in the browser and Play works
- [ ] `python -m pytest tests/ -q` green (13 tests)
- [ ] Laptop charged; PDF of the paper on the desktop
- [ ] Repo pushed, so github.com/Ivan825/Project-ONE matches what he sees
"""


if __name__ == "__main__":
    main()
