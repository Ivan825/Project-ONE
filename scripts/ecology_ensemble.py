#!/usr/bin/env python3
"""Do the headline results depend on the baseline ecology?

Every review of this work raises "a single ecology and parameter family". This
script answers it with a randomized ensemble rather than a parameter sweep: it
samples alternative viable ecologies, then re-tests only the paper's headline
claims in each one.

THE ANTI-CHERRY-PICKING DISCIPLINE, which is the point of the design:

  Stage 1 (screen)   samples candidate ecologies and runs ONLY the no-broadcast
                     baseline (condition A) in each. Viability is decided by
                     the criteria in VIABILITY below, which are fixed in this
                     file BEFORE any broadcast condition is run. The viable set
                     is frozen to viability.json and never revisited.
  Stage 2 (run)      runs the treatment conditions in the frozen viable set.
  Stage 3 (analyze)  tests the headline claims per ecology and counts how many
                     ecologies each one survives in.

Because Stage 1 cannot see any treatment outcome, no ecology can be admitted or
dropped on the basis of whether it produces the result we want.

Ecological parameters perturbed (+/-25% of baseline, independent uniform draws
from a fixed RandomState, so the sample is reproducible):

  resource_base_regen   resource inflow
  resource_capacity     resource abundance
  reproduce_cost        cost of reproduction
  metabolism            standing energy pressure
  action_cost           cost of maintaining/forming a link
  max_lifespan_mean     mortality pressure

Usage:
    python scripts/ecology_ensemble.py --screen     # stage 1, then STOP and read
    python scripts/ecology_ensemble.py --run        # stage 2 (resumable)
    python scripts/ecology_ensemble.py --analyze    # stage 3
"""
import argparse
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))
from project_one import Config, Simulation  # noqa: E402

OUT = os.path.join(ROOT, "campaigns", "ecology_ensemble")

# --- pre-registered design -------------------------------------------------
N_CANDIDATES = 24          # sampled; the viable subset is whatever survives
SCREEN_SEEDS = 3           # A-only runs per candidate in the viability screen
RUN_SEEDS = 10             # paired seeds per condition in the main ensemble
STEPS = 4000
SHOCK_STEP = 2000
SHOCK_FRACTION = 0.4
GAIN = 0.8
CONDITIONS = [("A", ""), ("B", ""), ("C", ""), ("F", "invert"), ("N", "")]
PERTURB = 0.25
SAMPLE_SEED = 20260820     # fixed, so the ensemble is reproducible

PARAMS = ["resource_base_regen", "resource_capacity", "reproduce_cost",
          "metabolism", "action_cost", "max_lifespan_mean"]

# --- PRE-REGISTERED VIABILITY CRITERIA -------------------------------------
# Fixed before any treatment condition is run. An ecology is viable iff its
# no-broadcast baseline satisfies ALL of these, in EVERY screen seed. They
# encode "a working ecology", not "an ecology that shows our effect".
VIABILITY = {
    "min_final_population": 20,      # did not collapse
    "max_population_fraction": 0.80,  # did not pin at the population cap
    "min_mean_degree": 2.0,          # network is not degenerate at t=shock
    "min_max_generation": 8,         # enough lineage depth for selection
}

# Metric definitions below are lifted from scripts/analyze_campaign.py so the
# ensemble tests the SAME quantities the paper reports, not lookalikes.
TRANSIENT = 500            # analyze_campaign.TRANSIENT
STRUCT_WIN = (500, 4000)   # window used for structural spillovers (Sect. 5.2)


def sample_ecologies():
    rng = np.random.RandomState(SAMPLE_SEED)
    base = Config()
    out = []
    for i in range(N_CANDIDATES):
        eco = {}
        for p in PARAMS:
            b = getattr(base, p)
            eco[p] = float(b * (1.0 + rng.uniform(-PERTURB, PERTURB)))
        out.append({"id": i, "params": eco})
    return out


def make_cfg(eco, cond, distortion):
    cfg = Config(condition=cond, distortion=distortion or "invert",
                 steps=STEPS, shock_step=SHOCK_STEP,
                 shock_fraction=SHOCK_FRACTION, feedback_gain=GAIN,
                 snapshot_interval=0)
    for k, v in eco["params"].items():
        setattr(cfg, k, v)
    return cfg


def one_run(job):
    eco, cond, distortion, seed = job
    sim = Simulation(make_cfg(eco, cond, distortion), seed=seed)
    sim.run()
    g = sim.global_memory
    pop = [s["population"] for s in g]

    # recovery_time_90, exactly as analyze_campaign.outcomes computes it
    pre_win = [p for s, p in zip(g, pop)
               if SHOCK_STEP - 500 <= s["t"] < SHOCK_STEP]
    baseline = sum(pre_win) / len(pre_win) if pre_win else 0.0
    rec, censored = STEPS - SHOCK_STEP, True
    for s, p in zip(g, pop):
        if s["t"] > SHOCK_STEP and baseline > 0 and p >= 0.9 * baseline:
            rec, censored = s["t"] - SHOCK_STEP, False
            break

    def first_last(key):
        a = next((s.get(key) for s in g if key in s), None)
        b = next((s.get(key) for s in reversed(g) if key in s), None)
        return a, b

    def mean_from(key, t0):
        v = [s[key] for s in g if s.get("t", 0) >= t0 and key in s]
        return float(np.mean(v)) if v else None

    def median_win(key, w=STRUCT_WIN):
        v = [s[key] for s in g if w[0] <= s.get("t", 0) <= w[1] and key in s]
        return float(np.median(v)) if v else None

    a_gs, b_gs = first_last("mean_trait_global_sensitivity")
    at_shock = [s for s in g if s.get("t") == SHOCK_STEP]
    post = [s for s in g if s.get("t", 0) > SHOCK_STEP]
    return {
        "eco": eco["id"], "cond": cond, "distortion": distortion, "seed": seed,
        # viability-screen fields
        "final_population": g[-1].get("population", 0),
        "mean_degree_at_shock": (at_shock[0]["mean_degree"] if at_shock else 0.0),
        "max_generation": max((a.generation for a in sim.agents.values()),
                              default=0),
        # headline-claim outcomes, paper definitions
        "recovery_time_90": rec,
        "recovery_censored": censored,
        "cooperation_rate": mean_from("cooperation", TRANSIENT),
        "trait_gs_delta": (None if a_gs is None or b_gs is None
                           else b_gs - a_gs),
        "fragmentation_post": (float(np.mean([s["fragmentation"] for s in post]))
                               if post else None),
        "mean_degree": median_win("mean_degree"),
        "freeman_centralization": median_win("freeman_centralization"),
        "betweenness_concentration": median_win("betweenness_concentration"),
        "state_hash": sim.state_hash(),
    }


def execute(jobs, label, checkpoint=None):
    """Run jobs on a process pool, appending each result to `checkpoint`
    (JSONL) as it lands so a killed run can be resumed rather than repeated."""
    workers = max(1, (os.cpu_count() or 2))
    print(f"{label}: {len(jobs)} runs on {workers} workers", flush=True)
    rows, done = [], 0
    fh = open(checkpoint, "a") if checkpoint else None
    try:
        with ProcessPoolExecutor(max_workers=workers) as ex:
            futs = [ex.submit(one_run, j) for j in jobs]
            for f in as_completed(futs):
                r = f.result()
                rows.append(r)
                if fh:
                    fh.write(json.dumps(r) + "\n")
                    fh.flush()
                done += 1
                if done % 20 == 0 or done == len(jobs):
                    print(f"  {done}/{len(jobs)}", flush=True)
    finally:
        if fh:
            fh.close()
    return rows


def screen():
    os.makedirs(OUT, exist_ok=True)
    ecos = sample_ecologies()
    jobs = [(e, "A", "", s) for e in ecos for s in range(1, SCREEN_SEEDS + 1)]
    rows = execute(jobs, "viability screen (baseline only)")

    cap = Config().max_population
    verdicts = {}
    for e in ecos:
        mine = [r for r in rows if r["eco"] == e["id"]]
        checks = {
            "min_final_population": all(
                r["final_population"] >= VIABILITY["min_final_population"]
                for r in mine),
            "max_population_fraction": all(
                r["final_population"] <= VIABILITY["max_population_fraction"] * cap
                for r in mine),
            "min_mean_degree": all(
                r["mean_degree_at_shock"] >= VIABILITY["min_mean_degree"]
                for r in mine),
            "min_max_generation": all(
                r["max_generation"] >= VIABILITY["min_max_generation"]
                for r in mine),
        }
        verdicts[e["id"]] = {"viable": all(checks.values()), "checks": checks,
                             "params": e["params"],
                             "screen": [{k: r[k] for k in
                                         ("seed", "final_population",
                                          "mean_degree_at_shock",
                                          "max_generation")} for r in mine]}

    viable = sorted(i for i, v in verdicts.items() if v["viable"])
    payload = {"criteria": VIABILITY, "sample_seed": SAMPLE_SEED,
               "perturbation": PERTURB, "params_perturbed": PARAMS,
               "n_candidates": N_CANDIDATES, "screen_seeds": SCREEN_SEEDS,
               "viable_ids": viable, "verdicts": verdicts,
               "note": "Frozen before any treatment condition was run."}
    dest = os.path.join(OUT, "viability.json")
    with open(dest, "w") as f:
        json.dump(payload, f, indent=1)

    print(f"\nviable: {len(viable)}/{N_CANDIDATES} -> {viable}")
    for i, v in sorted(verdicts.items()):
        if not v["viable"]:
            failed = [k for k, ok in v["checks"].items() if not ok]
            print(f"  eco {i:2d} REJECTED on {', '.join(failed)}")
    print(f"wrote {dest}")


def _load_checkpoint(path):
    rows = []
    if os.path.exists(path):
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
    return rows


def parse_ecos(spec):
    """"0-11" or "3,5,9" -> a set of ecology ids."""
    if not spec:
        return None
    out = set()
    for part in spec.split(","):
        if "-" in part:
            lo, hi = part.split("-")
            out.update(range(int(lo), int(hi) + 1))
        else:
            out.add(int(part))
    return out


def run(only=None, ckpt_name="runs.jsonl"):
    with open(os.path.join(OUT, "viability.json")) as f:
        via = json.load(f)
    ecos = {e["id"]: e for e in sample_ecologies()}
    ids = [i for i in via["viable_ids"] if only is None or i in only]
    jobs = [(ecos[i], c, d, s)
            for i in ids
            for c, d in CONDITIONS
            for s in range(1, RUN_SEEDS + 1)]
    if only is not None:
        print(f"slice: ecologies {sorted(ids)}")

    ckpt = os.path.join(OUT, ckpt_name)
    have = _load_checkpoint(ckpt)
    # Work already done by ANY machine counts as done: each machine appends to
    # its own checkpoint, but they all read every checkpoint present, so two
    # machines sharing a synced directory never repeat each other's runs.
    import glob
    seen = set()
    for other in sorted(glob.glob(os.path.join(OUT, "runs*.jsonl"))):
        for r in (have if os.path.abspath(other) == os.path.abspath(ckpt)
                  else _load_checkpoint(other)):
            seen.add((r["eco"], r["cond"], r.get("distortion", ""), r["seed"]))
    todo = [j for j in jobs
            if (j[0]["id"], j[1], j[2], j[3]) not in seen]
    if have:
        print(f"resuming: {len(have)} runs already on disk, {len(todo)} to go")

    fresh = execute(todo, "ensemble", checkpoint=ckpt) if todo else []
    rows = have + fresh
    if only is not None:
        print(f"slice complete: {len(rows)} runs in {ckpt}")
        return
    dest = os.path.join(OUT, "runs.json")
    with open(dest, "w") as f:
        json.dump({"rows": rows, "conditions": [c for c, _ in CONDITIONS],
                   "seeds": RUN_SEEDS, "gain": GAIN,
                   "shock_fraction": SHOCK_FRACTION, "steps": STEPS}, f,
                  indent=1)
    print(f"wrote {dest}  ({len(rows)} runs)")


# --- stage 3: do the headline claims survive? ------------------------------
# Each entry: (label, outcome key, condition, expected sign of the paired
# difference against A). sign 0 means "the claim IS the null" (no difference).
CLAIMS = [
    ("cooperation up under truth",      "cooperation_rate",   "C", +1),
    ("attention falls under the lie",   "trait_gs_delta",     "F", -1),
    ("attention falls under noise",     "trait_gs_delta",     "N", -1),
    ("attention falls under truth",     "trait_gs_delta",     "C", -1),
    # Structural spillovers, Sect. 5.2. The paper reports mean degree for all
    # three broadcast conditions but Freeman/betweenness flattening only for
    # the two distortions -- truth was explicitly rescoped out of the
    # flattening claim, so C is carried here as a check on that scoping.
    ("network densifies under truth",   "mean_degree",        "C", +1),
    ("network densifies under the lie", "mean_degree",        "F", +1),
    ("network densifies under noise",   "mean_degree",        "N", +1),
    ("hubs flatten under the lie",      "freeman_centralization", "F", -1),
    ("hubs flatten under noise",        "freeman_centralization", "N", -1),
    ("betweenness flattens under lie",  "betweenness_concentration", "F", -1),
    ("betweenness flattens under noise", "betweenness_concentration", "N", -1),
    ("recovery unaffected (truth)",     "recovery_time_90",   "C",  0),
    ("recovery unaffected (lie)",       "recovery_time_90",   "F",  0),
    ("recovery unaffected (noise)",     "recovery_time_90",   "N",  0),
    ("measurement alone is inert",      None,                 "B",  0),
]

INERT_KEYS = ("cooperation_rate", "trait_gs_delta", "mean_degree",
              "recovery_time_90", "fragmentation_post",
              "freeman_centralization", "betweenness_concentration")


def paired(rows, key, cond, ref="A"):
    """Paired Wilcoxon on per-seed differences; same treatment of exact ties
    and the same rank-biserial estimator as analyze_campaign.paired_compare."""
    by = {}
    for r in rows:
        if r.get(key) is None:
            continue
        by.setdefault(r["cond"], {})[r["seed"]] = r[key]
    from scipy.stats import rankdata, wilcoxon
    a, b = by.get(ref, {}), by.get(cond, {})
    seeds = sorted(set(a) & set(b))
    if len(seeds) < 5:
        return None
    d = np.array([b[s] - a[s] for s in seeds], float)
    if np.allclose(d, 0):
        return {"n": len(seeds), "median_diff": 0.0, "p": 1.0, "rb": 0.0,
                "all_zero": True}
    nz = d[d != 0]
    try:
        _, p = wilcoxon(nz, alternative="two-sided")
    except ValueError:
        p = 1.0
    ranks = rankdata(np.abs(nz), method="average")
    rb = (ranks[nz > 0].sum() - ranks[nz < 0].sum()) / ranks.sum()
    return {"n": len(seeds), "median_diff": float(np.median(d)),
            "p": float(p), "rb": float(rb), "all_zero": False}


def analyze():
    with open(os.path.join(OUT, "runs.json")) as f:
        data = json.load(f)
    with open(os.path.join(OUT, "viability.json")) as f:
        via = json.load(f)
    from scipy.stats import spearmanr
    rows = data["rows"]
    ecos = sorted({r["eco"] for r in rows})

    report = {"n_ecologies": len(ecos), "seeds": data["seeds"],
              "viable_of_candidates": f"{len(via['viable_ids'])}/{via['n_candidates']}",
              "claims": {}, "ordering": {}, "baseline_spread": {}}

    # How different ARE these ecologies?  If the baselines barely move, the
    # ensemble is not a real test, so this is reported alongside the claims.
    for key in ("mean_degree", "cooperation_rate", "final_population",
                "trait_gs_delta"):
        vals = [np.median([r[key] for r in rows
                           if r["eco"] == e and r["cond"] == "A"
                           and r.get(key) is not None]) for e in ecos]
        vals = [v for v in vals if not np.isnan(v)]
        report["baseline_spread"][key] = {
            "min": float(min(vals)), "max": float(max(vals)),
            "ratio": (float(max(vals) / min(vals)) if min(vals) > 0 else None)}

    print(f"ecologies: {len(ecos)}   seeds/condition: {data['seeds']}")
    print(f"viable at screen: {report['viable_of_candidates']}\n")
    print("baseline spread across ecologies (condition A):")
    for k, v in report["baseline_spread"].items():
        r = f"  ({v['ratio']:.1f}x)" if v["ratio"] else ""
        print(f"  {k:22s} {v['min']:9.3f} .. {v['max']:9.3f}{r}")

    print(f"\n{'claim':34s} {'holds':>7s} {'sign':>7s}   median effect")
    for label, key, cond, sign in CLAIMS:
        per = {}
        for e in ecos:
            sub = [r for r in rows if r["eco"] == e]
            if key is None:  # measurement-inertness: B identical to A on all
                res = {k: paired(sub, k, cond) for k in INERT_KEYS}
                ok = all(v is not None and v["all_zero"] for v in res.values())
                per[e] = {"identical": ok,
                          "nonzero_outcomes": [k for k, v in res.items()
                                               if v is not None
                                               and not v["all_zero"]]}
                continue
            st = paired(sub, key, cond)
            if st is None:
                continue
            if sign == 0:
                st["supports"] = bool(st["p"] > 0.05)
            else:
                st["supports"] = bool(np.sign(st["median_diff"]) == sign
                                      and st["p"] < 0.05)
            st["right_sign"] = (True if sign == 0 else
                                bool(np.sign(st["median_diff"]) == sign))
            per[e] = st

        if key is None:
            n_ok = sum(1 for v in per.values() if v["identical"])
            report["claims"][label] = {"per_ecology": per,
                                       "n_holding": n_ok, "n_total": len(per)}
            print(f"{label:34s} {n_ok:3d}/{len(per):<3d}       -   "
                  f"all per-seed differences exactly zero")
            continue

        n_ok = sum(1 for v in per.values() if v["supports"])
        n_sign = sum(1 for v in per.values() if v["right_sign"])
        meds = [v["median_diff"] for v in per.values()]
        report["claims"][label] = {
            "outcome": key, "condition": cond, "expected_sign": sign,
            "n_holding": n_ok, "n_right_sign": n_sign, "n_total": len(per),
            "median_effect_across_ecologies": float(np.median(meds)),
            "effect_range": [float(min(meds)), float(max(meds))],
            "per_ecology": per}
        print(f"{label:34s} {n_ok:3d}/{len(per):<3d} {n_sign:3d}/{len(per):<3d}   "
              f"{np.median(meds):+.4f}  [{min(meds):+.4f}, {max(meds):+.4f}]")

    # The ordering claim: false < noise < truth < silence in evolved attention.
    order_hits, rhos = 0, []
    per_eco_order = {}
    for e in ecos:
        med = {}
        for c in ("F", "N", "C", "A"):
            v = [r["trait_gs_delta"] for r in rows
                 if r["eco"] == e and r["cond"] == c
                 and r.get("trait_gs_delta") is not None]
            if v:
                med[c] = float(np.median(v))
        if len(med) < 4:
            continue
        seq = [med["F"], med["N"], med["C"], med["A"]]
        exact = all(seq[i] <= seq[i + 1] for i in range(3))
        rho = spearmanr([0, 1, 2, 3], seq).correlation
        order_hits += int(exact)
        rhos.append(float(rho))
        per_eco_order[e] = {"medians": med, "exact_order": bool(exact),
                            "rho": float(rho)}
    report["ordering"] = {"claim": "F <= N <= C <= A in evolved attention",
                          "n_exact": order_hits, "n_total": len(per_eco_order),
                          "median_rho": float(np.median(rhos)) if rhos else None,
                          "per_ecology": per_eco_order}
    print(f"\nordering F<=N<=C<=A holds exactly in "
          f"{order_hits}/{len(per_eco_order)} ecologies; "
          f"median rank correlation {np.median(rhos):+.2f}")

    dest = os.path.join(OUT, "ensemble_report.json")
    with open(dest, "w") as f:
        json.dump(report, f, indent=1)
    print(f"\nwrote {dest}")


def merge():
    """Fold every runs*.jsonl in the output dir into runs.json, de-duplicating
    on (ecology, condition, distortion, seed). Runs are deterministic, so a
    duplicate is a duplicate, not a conflict."""
    import glob
    seen, rows, checked, clashes = {}, [], 0, []
    for path in sorted(glob.glob(os.path.join(OUT, "runs*.jsonl"))):
        n0 = len(rows)
        for r in _load_checkpoint(path):
            key = (r["eco"], r["cond"], r.get("distortion", ""), r["seed"])
            if key in seen:
                # Overlap between machines is free cross-platform verification:
                # the same (config, seed) must give the same state hash on a
                # different CPU architecture, Python and networkx.
                checked += 1
                if seen[key]["state_hash"] != r["state_hash"]:
                    clashes.append(key)
                continue
            seen[key] = r
            rows.append(r)
        print(f"  {os.path.basename(path)}: +{len(rows) - n0} new")
    if checked:
        print(f"  cross-checked {checked} duplicated runs: "
              f"{'all hashes agree' if not clashes else f'{len(clashes)} MISMATCH {clashes[:5]}'}")
        if clashes:
            raise SystemExit("state hashes disagree across machines; "
                             "do not merge these results")
    with open(os.path.join(OUT, "viability.json")) as f:
        via = json.load(f)
    want = len(via["viable_ids"]) * len(CONDITIONS) * RUN_SEEDS
    dest = os.path.join(OUT, "runs.json")
    with open(dest, "w") as f:
        json.dump({"rows": rows, "conditions": [c for c, _ in CONDITIONS],
                   "seeds": RUN_SEEDS, "gain": GAIN,
                   "shock_fraction": SHOCK_FRACTION, "steps": STEPS}, f,
                  indent=1)
    print(f"wrote {dest}: {len(rows)}/{want} runs"
          f"{'' if len(rows) == want else '  (INCOMPLETE)'}")
    return len(rows) == want


def validate():
    """Two checks in one, both against ground truth rather than against us.

    The ensemble runs the harsh-shock protocol exactly (4000 steps, shock at
    2000, 40% hub removal, gain 0.8), so at UNPERTURBED parameters it must
    reproduce the stored harsh_shock campaign run-for-run. That simultaneously
    proves (a) the outcome definitions copied from analyze_campaign.py are the
    same quantities the paper reports, and (b) the engine's v1 path is
    unchanged by the v2 policy machinery -- per-run outcomes are a far more
    sensitive drift detector than any summary statistic."""
    with open(os.path.join(ROOT, "campaigns", "harsh_shock",
                           "results.json")) as f:
        ref = json.load(f)["outcomes_per_run"]
    base = {"id": "baseline", "params": {}}   # no perturbation at all
    keys = ("recovery_time_90", "fragmentation_post", "cooperation_rate",
            "trait_gs_delta")
    bad = 0
    for cond, dist in [("A", ""), ("C", "")]:
        for seed in (1, 2):
            want = next((o for o in ref if o["condition"] == cond
                         and o["seed"] == seed), None)
            if want is None:
                continue
            got = one_run((base, cond, dist, seed))
            print(f"{cond} seed {seed}")
            for k in keys:
                a_, b_ = want.get(k), got.get(k)
                ok = (a_ is not None and b_ is not None
                      and abs(float(a_) - float(b_)) < 1e-6)
                bad += (not ok)
                print(f"   {k:20s} stored {a_!s:>12.12}  ensemble {b_!s:>12.12}"
                      f"   {'ok' if ok else 'MISMATCH'}")
    print("\nvalidation:", "PASS" if bad == 0 else f"FAIL ({bad} mismatches)")
    return bad


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--screen", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--analyze", action="store_true")
    ap.add_argument("--merge", action="store_true")
    ap.add_argument("--validate", action="store_true")
    ap.add_argument("--only-ecos", default=None,
                    help="restrict --run to a slice, e.g. 12-23 or 3,5,9")
    ap.add_argument("--checkpoint", default="runs.jsonl",
                    help="checkpoint filename, so two machines do not collide")
    a = ap.parse_args()
    if a.screen:
        screen()
    elif a.run:
        run(parse_ecos(a.only_ecos), a.checkpoint)
    elif a.merge:
        merge()
    elif a.analyze:
        analyze()
    elif a.validate:
        sys.exit(1 if validate() else 0)
    else:
        ap.print_help()
