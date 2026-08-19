#!/usr/bin/env python3
"""Individual-level diagnostics for the evolved decline in global sensitivity.

The sweep and the two architectural controls establish THAT mean gamma falls
under high-drive broadcasts. This script asks what the individual-level
pathway is, and rules out the two simplest candidates. Every quantity the
paper reports about the mechanism (Sect. 5.5) is computed here.

Reported per condition:

  generations       lineage depth actually traversed (max generation reached,
                    and the mean generation of agents alive at the end) --
                    substantiates the "~N generations" claim.
  rho_offspring     within-run Spearman rho between an agent's gamma and its
                    lifetime offspring count, over all agents that reached
                    reproductive age. A NEGATIVE marginal fecundity gradient
                    would be the simplest explanation of the decline; it is
                    not what the data show.
  shock_selectivity mean gamma of shock victims minus mean gamma of the
                    population alive at the shock step. Hub removal is
                    gamma-correlated only if high-gamma agents are hubs.
  no_shock_decline  the same sweep cell rerun with the shock disabled, to
                    show the decline does not require the shock at all.

Runs are deterministic given (config, seed); no stored campaign is modified.

    python scripts/selection_mechanism.py [--seeds 5]
"""
import argparse
import json
import os
import statistics
import sys

from scipy.stats import spearmanr

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "src"))
from project_one import Config, Simulation  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAMMA = "global_sensitivity"
# The high-drive cell the paper discusses: harsh shock, g=0.8, 4000 steps.
BASE = dict(steps=4000, shock_step=2000, shock_fraction=0.4,
            feedback_gain=0.8, snapshot_interval=0)


def run(cond, seed, distortion="invert", shock=True):
    kw = dict(BASE)
    if not shock:
        kw["shock_step"] = 0
        kw["shock_fraction"] = 0.0
    cfg = Config(condition=cond, distortion=distortion, **kw)
    sim = Simulation(cfg, seed=seed)
    sim.run()
    return sim


def gamma_delta(sim):
    g = sim.global_memory
    first = next((s[f"mean_trait_{GAMMA}"] for s in g
                  if f"mean_trait_{GAMMA}" in s), None)
    last = next((s[f"mean_trait_{GAMMA}"] for s in reversed(g)
                 if f"mean_trait_{GAMMA}" in s), None)
    return None if first is None or last is None else last - first


def diagnostics(sim):
    agents = list(sim.agents.values())
    gens = [a.generation for a in agents]
    alive = [a for a in agents if a.alive]

    # Fecundity gradient: only agents that lived long enough to reproduce at
    # all can inform it; including infant deaths would measure survival, not
    # fecundity.
    fertile = [a for a in agents
               if a.age >= sim.cfg.min_reproduce_age and not a.alive]
    if len(fertile) > 10:
        rho, p = spearmanr([a.traits[GAMMA] for a in fertile],
                           [a.offspring_count for a in fertile])
    else:
        rho, p = float("nan"), float("nan")

    victims = [a for a in agents if a.cause_of_death == "shock"]
    at_shock = [a for a in agents
                if a.birth_time <= sim.cfg.shock_step
                and (a.death_time is None or a.death_time >= sim.cfg.shock_step)]
    if victims and at_shock:
        sel = (statistics.fmean(a.traits[GAMMA] for a in victims)
               - statistics.fmean(a.traits[GAMMA] for a in at_shock))
    else:
        sel = None

    return {
        "max_generation": max(gens),
        "mean_generation_alive": (statistics.fmean(a.generation for a in alive)
                                  if alive else None),
        "n_agents_ever": len(agents),
        "n_fertile": len(fertile),
        "rho_gamma_offspring": float(rho),
        "p_rho": float(p),
        "shock_selectivity_gamma": sel,
        "n_shock_victims": len(victims),
        "dgamma": gamma_delta(sim),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=5)
    args = ap.parse_args()
    seeds = list(range(1, args.seeds + 1))

    out = {"config": BASE, "seeds": seeds, "conditions": {}}
    for label, cond, dist in [("A", "A", "invert"), ("C", "C", "invert"),
                              ("F:invert", "F", "invert")]:
        rows = [diagnostics(run(cond, s, dist)) for s in seeds]
        agg = {k: [r[k] for r in rows] for k in rows[0]}
        out["conditions"][label] = {
            "per_seed": rows,
            "max_generation": max(agg["max_generation"]),
            "median_mean_generation_alive":
                statistics.median(agg["mean_generation_alive"]),
            "median_rho_gamma_offspring":
                statistics.median(agg["rho_gamma_offspring"]),
            "median_shock_selectivity":
                statistics.median([v for v in agg["shock_selectivity_gamma"]
                                   if v is not None] or [float("nan")]),
            "median_dgamma": statistics.median(agg["dgamma"]),
        }
        print(f"{label:9s} max_gen={out['conditions'][label]['max_generation']:3d} "
              f"mean_gen_alive={out['conditions'][label]['median_mean_generation_alive']:5.1f} "
              f"rho(gamma,offspring)={out['conditions'][label]['median_rho_gamma_offspring']:+.3f} "
              f"shock_sel={out['conditions'][label]['median_shock_selectivity']:+.3f} "
              f"dgamma={out['conditions'][label]['median_dgamma']:+.3f}")

    # Does the decline survive removing the shock entirely?
    ns = [gamma_delta(run("F", s, "invert", shock=False)) for s in seeds]
    out["no_shock"] = {"F_median_dgamma": statistics.median(ns),
                       "per_seed": ns}
    print(f"\nF:invert without any shock: dgamma median "
          f"{out['no_shock']['F_median_dgamma']:+.3f} "
          f"(vs {out['conditions']['F:invert']['median_dgamma']:+.3f} with shock)")

    dest = os.path.join(ROOT, "campaigns", "selection_mechanism.json")
    with open(dest, "w") as f:
        json.dump(out, f, indent=1)
    print(f"wrote {dest}")


if __name__ == "__main__":
    main()
