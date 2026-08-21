#!/usr/bin/env python3
"""Paper 2 main campaign: which response rules does selection favour?

Runs the v2 architecture (heritable response policy W, see
docs/PAPER2_PLAN.md) across the same conditions, protocol and horizon as
Paper 1's harsh-shock campaign, and measures selection on W directly with the
Robertson/Price selection differential validated in scripts/policy_pilot.py.

Every design choice below was fixed BEFORE any treatment condition was run.
The pilot that fixed them used condition A only, where W is causally inert, so
none of them could have been chosen to produce a result.

    --run       A/B/C/F/N x SEEDS paired, under evolved AND fixed policies
    --analyze   the pre-registered tests below, and nothing else as confirmatory
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
from project_one import Config, Simulation                 # noqa: E402
from project_one.agents import (POLARITY_KEYS, POLICY_KEYS,  # noqa: E402
                                TRAITS)

OUT = os.path.join(ROOT, "campaigns", "policy_campaign")

# --- protocol: identical to Paper 1's harsh shock, so the two are comparable
STEPS = 4000               # fixed by the pilot on cohort-precision grounds
SHOCK_STEP = 2000
SHOCK_FRACTION = 0.4
GAIN = 0.8
SEEDS = 30                 # pilot MDE at n=30: S = 0.0035, vs S(risk) = 0.011
CONDITIONS = [("A", ""), ("B", ""), ("C", ""), ("F", "invert"), ("N", "")]
MODES = ["evolved", "fixed", "polarity"]
# "fixed"    IS Paper 1's engine and protocol: doubles as an exact replication.
# "evolved"  the 64-cell policy. H1 below is its pre-registered test.
# "polarity" the 4-scalar design, added AFTER H1 came back null -- the null is
#            the reason for it and is reported, not replaced. rho == 1 is the
#            hand-written rule bit-identically, so the rule is a verified point
#            in the searched space rather than an argued one.
COHORT_WINDOW = (500, STEPS)   # completed lifetimes only, post-transient

# --- PRE-REGISTERED HYPOTHESES ---------------------------------------------
# Stated before the first treatment run. The PRIMARY test is a single number
# per run, so it carries no multiplicity burden; the per-cell tests are
# secondary and are read through Benjamini-Hochberg and effect size.
#
# PRIMARY (one per treatment condition, paired against A on seed):
#   H1  Is the response policy under selection at all?
#       Statistic: rms_S = sqrt(mean_k S(W_k)^2), one number per run.
#       Under A, W cannot affect behaviour, so rms_S there is the exact
#       sampling floor. Test: rms_S(treatment) > rms_S(A), paired Wilcoxon.
#
# SECONDARY:
#   H2  WHICH parts of the policy are selected: per-cell S(W_k) vs A, 64
#       contrasts, BH-corrected, reported with effect sizes.
#   H3  Does freeing the policy change selection on attention itself?
#       S(global_sensitivity) under evolved vs under fixed, per condition.
#   H4  Paper 1's own statistic, re-measured here: dgamma vs A, evolved and
#       fixed. Under "fixed" this is a direct replication of Paper 1.
#   H5  Substitution: is the gamma decline SMALLER when the population has a
#       second exit (zeroing W) available? dgamma(evolved) vs dgamma(fixed),
#       paired on seed within condition.
#   H6  Is the behavioural taxonomy RECOVERED rather than assumed: do the
#       standard outcomes under evolved policies order across conditions the
#       way Paper 1's hand-written rules produce?
#
#   H7  Is the LOW-DIMENSIONAL policy under selection, where the 64-cell one
#       was not? Per-channel S(rho_a), 4 contrasts, paired against A.
#   H8  Where does selection push the response? rho-bar vs 1.0 (the
#       hand-written rule), per channel per condition: toward indifference
#       (rho -> 0), toward inversion (rho < 0), or toward amplification.
#
# Anything not in this list is exploratory and is labelled as such.


def cfg_for(cond, distortion, mode, gain=GAIN, rule="corrective"):
    return Config(condition=cond, distortion=distortion or "invert",
                  steps=STEPS, shock_step=SHOCK_STEP,
                  shock_fraction=SHOCK_FRACTION, feedback_gain=gain,
                  response_mode=rule,
                  policy_mode=mode, policy_log_interval=STEPS // 4,
                  snapshot_interval=0)


def selection_differential(sim, keys, getter, t0, t1):
    """S(z) = cov(z_i, n_i) / n-bar over completed lifetimes in [t0, t1]."""
    cohort = [a for a in sim.agents.values()
              if a.death_time is not None
              and a.birth_time >= t0 and a.death_time <= t1
              and getter(a) is not None]
    if len(cohort) < 100:
        return None
    n = np.array([a.offspring_count for a in cohort], float)
    if n.mean() <= 0:
        return None
    out = {}
    for k in keys:
        z = np.array([getter(a)[k] for a in cohort], float)
        out[k] = float(np.cov(z, n, bias=True)[0, 1] / n.mean())
    return out


def one_run(job):
    cond, distortion, mode, seed = job[:4]
    gain = job[4] if len(job) > 4 else GAIN
    rule = job[5] if len(job) > 5 else "corrective"
    sim = Simulation(cfg_for(cond, distortion, mode, gain, rule), seed=seed)
    sim.run()
    g = sim.global_memory
    pop = [s["population"] for s in g]

    pre = [p for s, p in zip(g, pop) if SHOCK_STEP - 500 <= s["t"] < SHOCK_STEP]
    base = sum(pre) / len(pre) if pre else 0.0
    rec = STEPS - SHOCK_STEP
    for s, p in zip(g, pop):
        if s["t"] > SHOCK_STEP and base > 0 and p >= 0.9 * base:
            rec = s["t"] - SHOCK_STEP
            break

    def fl(key):
        a = next((s.get(key) for s in g if key in s), None)
        b = next((s.get(key) for s in reversed(g) if key in s), None)
        return (None if a is None or b is None else b - a)

    def mean_from(key, t0=500):
        # analyze_campaign uses t >= TRANSIENT for cooperation but t > shock for
        # post-shock fragmentation; `strict` keeps that asymmetry exact rather
        # than approximately right.
        v = [s[key] for s in g if s.get("t", 0) >= t0 and key in s]
        return float(np.mean(v)) if v else None

    def mean_after(key, t0):
        v = [s[key] for s in g if s.get("t", 0) > t0 and key in s]
        return float(np.mean(v)) if v else None

    def median_win(key, w=(500, STEPS)):
        v = [s[key] for s in g if w[0] <= s.get("t", 0) <= w[1] and key in s]
        return float(np.median(v)) if v else None

    S_traits = selection_differential(sim, TRAITS, lambda a: a.traits,
                                      *COHORT_WINDOW)
    pkeys = (POLICY_KEYS if mode == "evolved"
             else POLARITY_KEYS if mode == "polarity" else None)
    S_policy = (selection_differential(sim, pkeys, lambda a: a.policy,
                                       *COHORT_WINDOW) if pkeys else None)
    full = [s for s in g if "mean_policy" in s]
    lin = [s["lineage_effective_n"] for s in g if "lineage_effective_n" in s]

    return {
        "cond": cond, "distortion": distortion, "mode": mode, "seed": seed,
        "gain": gain, "rule": rule,
        "final_population": g[-1].get("population", 0),
        "max_generation": max((a.generation for a in sim.agents.values()),
                              default=0),
        "lineage_effective_n": float(np.median(lin)) if lin else None,
        # Paper 1's outcomes, so the taxonomy check (H6) uses the same numbers
        "recovery_time_90": rec,
        "cooperation_rate": mean_from("cooperation"),
        "fragmentation_post": mean_after("fragmentation", SHOCK_STEP),
        "mean_degree": median_win("mean_degree"),
        "freeman_centralization": median_win("freeman_centralization"),
        "trait_gs_delta": fl("mean_trait_global_sensitivity"),
        # Paper 2's measurement
        "S_traits": S_traits,
        "S_policy": S_policy,
        "rms_S": (float(np.sqrt(np.mean(np.square(list(S_policy.values())))))
                  if S_policy else None),
        "dW": ({k: full[-1]["mean_policy"][k] - full[0]["mean_policy"][k]
                for k in pkeys} if pkeys and len(full) >= 2 else None),
        # Level, not change: for polarity the question is where rho SITS
        # relative to 1.0, the hand-written rule.
        "W_final": ({k: full[-1]["mean_policy"][k] for k in pkeys}
                    if pkeys and full else None),
        "state_hash": sim.state_hash(),
    }


def _load(path):
    rows = []
    if os.path.exists(path):
        with open(path) as f:
            for line in f:
                if line.strip():
                    rows.append(json.loads(line))
    return rows


def run(only_mode=None, ckpt_name="runs.jsonl", gain=GAIN, rule="corrective",
        seeds=SEEDS, conds=None):
    os.makedirs(OUT, exist_ok=True)
    modes = [only_mode] if only_mode else MODES
    use = [(c, d) for c, d in CONDITIONS if conds is None or c in conds]
    jobs = [(c, d, m, s, gain, rule) for m in modes for c, d in use
            for s in range(1, seeds + 1)]
    ckpt = os.path.join(OUT, ckpt_name)
    import glob
    seen = set()
    for other in sorted(glob.glob(os.path.join(OUT, "runs*.jsonl"))):
        for r in _load(other):
            seen.add((r["cond"], r.get("distortion", ""), r["mode"], r["seed"],
                      r.get("gain", GAIN), r.get("rule", "corrective")))
    todo = [j for j in jobs if j not in seen]
    if len(todo) < len(jobs):
        print(f"resuming: {len(jobs) - len(todo)} done, {len(todo)} to go")

    workers = max(1, os.cpu_count() or 2)
    print(f"policy campaign: {len(todo)} runs on {workers} workers", flush=True)
    done = 0
    with open(ckpt, "a") as fh, ProcessPoolExecutor(max_workers=workers) as ex:
        futs = [ex.submit(one_run, j) for j in todo]
        for f in as_completed(futs):
            fh.write(json.dumps(f.result()) + "\n")
            fh.flush()
            done += 1
            if done % 10 == 0 or done == len(todo):
                print(f"  {done}/{len(todo)}", flush=True)
    print(f"wrote {ckpt}")


def merge():
    import glob
    seen, rows, checked, bad = {}, [], 0, []
    for path in sorted(glob.glob(os.path.join(OUT, "runs*.jsonl"))):
        n0 = len(rows)
        for r in _load(path):
            key = (r["cond"], r.get("distortion", ""), r["mode"], r["seed"],
                   r.get("gain", GAIN), r.get("rule", "corrective"))
            if key in seen:
                checked += 1
                if seen[key]["state_hash"] != r["state_hash"]:
                    bad.append(key)
                continue
            seen[key] = r
            rows.append(r)
        print(f"  {os.path.basename(path)}: +{len(rows) - n0}")
    if checked:
        print(f"  cross-checked {checked}: "
              f"{'all agree' if not bad else f'{len(bad)} MISMATCH'}")
        if bad:
            raise SystemExit("hashes disagree across machines")
    dest = os.path.join(OUT, "runs.json")
    with open(dest, "w") as f:
        json.dump({"rows": rows, "seeds": SEEDS, "steps": STEPS,
                   "gain": GAIN, "shock_fraction": SHOCK_FRACTION}, f)
    # The main design is MODES x CONDITIONS x SEEDS at gain 0.8, corrective.
    # Sweep arms are extra and counted separately rather than folded into a
    # completeness fraction they would silently inflate.
    want = len(MODES) * len(CONDITIONS) * SEEDS
    main = [r for r in rows if r.get("gain", GAIN) == GAIN
            and r.get("rule", "corrective") == "corrective"]
    extra = len(rows) - len(main)
    # Seed counts vary by arm (the H7 follow-up extended polarity to 100), so
    # report the design cell by cell instead of a fraction that reads as
    # "incomplete" when an arm was deliberately deepened.
    have = {}
    for r in main:
        have.setdefault(r["mode"], {}).setdefault(r["cond"], set()).add(r["seed"])
    short = [f"{m}/{c}={len(v)}" for m, d in sorted(have.items())
             for c, v in sorted(d.items()) if len(v) < SEEDS]
    print(f"wrote {dest}: {len(rows)} runs "
          f"({len(main)} at gain {GAIN}/corrective, {extra} in sweeps)")
    print("  seeds per cell: " + ", ".join(
        f"{m} {min(len(v) for v in d.values())}-{max(len(v) for v in d.values())}"
        for m, d in sorted(have.items())) +
        (f"   BELOW {SEEDS}: {', '.join(short)}" if short else
         f"   (all cells >= the {SEEDS}-seed design)"))


def paired(rows, key, cond, mode, ref="A", refmode=None):
    from scipy.stats import rankdata, wilcoxon
    refmode = refmode or mode
    a = {r["seed"]: r[key] for r in rows
         if r["cond"] == ref and r["mode"] == refmode and r.get(key) is not None}
    b = {r["seed"]: r[key] for r in rows
         if r["cond"] == cond and r["mode"] == mode and r.get(key) is not None}
    seeds = sorted(set(a) & set(b))
    if len(seeds) < 5:
        return None
    d = np.array([b[s] - a[s] for s in seeds], float)
    if np.allclose(d, 0):
        return {"n": len(seeds), "median_diff": 0.0, "p": 1.0, "rb": 0.0}
    nz = d[d != 0]
    try:
        _, p = wilcoxon(nz, alternative="two-sided")
    except ValueError:
        p = 1.0
    ranks = rankdata(np.abs(nz), method="average")
    rb = (ranks[nz > 0].sum() - ranks[nz < 0].sum()) / ranks.sum()
    return {"n": len(seeds), "median_diff": float(np.median(d)),
            "p": float(p), "rb": float(rb)}


def analyze():
    with open(os.path.join(OUT, "runs.json")) as f:
        allrows = json.load(f)["rows"]
    # The headline tables are the main design point: gain 0.8, corrective rule.
    # Sweep cells live in their own section so nothing is silently pooled.
    rows = [r for r in allrows if r.get("gain", GAIN) == GAIN
            and r.get("rule", "corrective") == "corrective"]
    rep = {}
    print(f"runs: {len(rows)}   seeds: {SEEDS}   horizon: {STEPS}\n")

    print("H1 (PRIMARY)  is the response policy under selection at all?")
    print(f"  {'cond':>5} {'median rms_S diff vs A':>24} {'r':>7} {'p':>10}")
    rep["H1"] = {}
    for cond, _ in CONDITIONS[1:]:
        st = paired(rows, "rms_S", cond, "evolved")
        if st:
            rep["H1"][cond] = st
            print(f"  {cond:>5} {st['median_diff']:+24.5f} {st['rb']:+7.2f} "
                  f"{st['p']:10.4f}")

    print("\nH2 (secondary) which policy cells are selected (BH over 64)")
    from scipy.stats import rankdata as _rd
    rep["H2"] = {}
    for cond, _ in CONDITIONS[2:]:
        cells = {}
        for k in POLICY_KEYS:
            a = {r["seed"]: r["S_policy"][k] for r in rows
                 if r["cond"] == "A" and r["mode"] == "evolved" and r["S_policy"]}
            b = {r["seed"]: r["S_policy"][k] for r in rows
                 if r["cond"] == cond and r["mode"] == "evolved" and r["S_policy"]}
            seeds = sorted(set(a) & set(b))
            if len(seeds) < 5:
                continue
            d = np.array([b[s] - a[s] for s in seeds])
            from scipy.stats import wilcoxon
            try:
                _, p = wilcoxon(d, alternative="two-sided")
            except ValueError:
                p = 1.0
            cells[k] = {"median_diff": float(np.median(d)), "p": float(p)}
        ps = np.array([v["p"] for v in cells.values()])
        order = np.argsort(ps)
        m = len(ps)
        bh = np.zeros(m, bool)
        for rank, idx in enumerate(order, start=1):
            if ps[idx] <= 0.05 * rank / m:
                bh[order[:rank]] = True
        keys = list(cells)
        surv = [keys[i] for i in range(m) if bh[i]]
        for k, ok in zip(keys, bh):
            cells[k]["bh"] = bool(ok)
        rep["H2"][cond] = cells
        top = sorted(surv, key=lambda k: -abs(cells[k]["median_diff"]))[:5]
        print(f"  {cond}: {len(surv)}/{m} cells survive BH." +
              ("  strongest: " + ", ".join(
                  f"{k} {cells[k]['median_diff']:+.4f}" for k in top)
               if top else ""))

    print("\nH3/H4/H5  attention: selection on gamma, and its decline")
    print(f"  {'cond':>5} {'mode':>8} {'S(gamma) vs A':>15} {'dgamma vs A':>13} {'p':>9}")
    rep["H3"], rep["H4"] = {}, {}
    for mode in MODES:
        for cond, _ in CONDITIONS[2:]:
            sg = paired([{**r, "S_gs": (r.get("S_traits") or {}).get(
                "global_sensitivity")} for r in rows], "S_gs", cond, mode)
            dg = paired(rows, "trait_gs_delta", cond, mode)
            if sg and dg:
                rep["H3"].setdefault(mode, {})[cond] = sg
                rep["H4"].setdefault(mode, {})[cond] = dg
                print(f"  {cond:>5} {mode:>8} {sg['median_diff']:+15.5f} "
                      f"{dg['median_diff']:+13.4f} {dg['p']:9.4f}")

    print("\nH5  substitution: is the gamma decline smaller when W is free?")
    rep["H5"] = {}
    for cond, _ in CONDITIONS[2:]:
        st = paired(rows, "trait_gs_delta", cond, "evolved",
                    ref=cond, refmode="fixed")
        if st:
            rep["H5"][cond] = st
            direction = ("smaller decline under evolved"
                         if st["median_diff"] > 0 else
                         "larger decline under evolved")
            print(f"  {cond}: evolved - fixed = {st['median_diff']:+.4f} "
                  f"(p={st['p']:.4f})  {direction}")

    print("\nH6  is the behavioural taxonomy recovered rather than assumed?")
    rep["H6"] = {}
    for key in ("cooperation_rate", "fragmentation_post", "mean_degree"):
        line = []
        for mode in MODES:
            for cond, _ in CONDITIONS[2:]:
                st = paired(rows, key, cond, mode)
                if st:
                    rep["H6"].setdefault(key, {}).setdefault(mode, {})[cond] = st
                    line.append(f"{mode[0]}/{cond} {st['median_diff']:+.3f}")
        print(f"  {key:20s} " + "  ".join(line))

    have_pol = any(r["mode"] == "polarity" for r in rows)
    if have_pol:
        print("\nH7  is the LOW-DIMENSIONAL policy under selection?")
        print(f"  {'cond':>5} {'channel':>9} {'S(rho) vs A':>13} {'p':>9}")
        rep["H7"] = {}
        for cond, _ in CONDITIONS[2:]:
            for k in POLARITY_KEYS:
                st = paired([{**r, "s": (r.get("S_policy") or {}).get(k)}
                             for r in rows], "s", cond, "polarity")
                if st:
                    rep["H7"].setdefault(cond, {})[k] = st
                    flag = " *" if st["p"] < 0.05 else ""
                    print(f"  {cond:>5} {k:>9} {st['median_diff']:+13.5f} "
                          f"{st['p']:9.4f}{flag}")

        print("\nH8  where does selection push the response? "
              "(rho = 1 is the hand-written rule)")
        print(f"  {'cond':>5} {'channel':>9} {'rho-bar':>9} {'vs A':>9} {'p':>9}")
        rep["H8"] = {}
        for cond, _ in CONDITIONS[2:]:
            for k in POLARITY_KEYS:
                lvl = [r["W_final"][k] for r in rows if r["mode"] == "polarity"
                       and r["cond"] == cond and r.get("W_final")]
                st = paired([{**r, "w": (r.get("W_final") or {}).get(k)}
                             for r in rows], "w", cond, "polarity")
                if lvl and st:
                    rep["H8"].setdefault(cond, {})[k] = {
                        "rho_bar": float(np.median(lvl)), **st}
                    flag = " *" if st["p"] < 0.05 else ""
                    print(f"  {cond:>5} {k:>9} {np.median(lvl):+9.4f} "
                          f"{st['median_diff']:+9.4f} {st['p']:9.4f}{flag}")

    # --- sweep cells, reported separately so nothing is pooled silently ----
    gains = sorted({r.get("gain", GAIN) for r in allrows
                    if r["mode"] == "polarity"
                    and r.get("rule", "corrective") == "corrective"})
    if len(gains) > 1:
        print("\nGAIN SWEEP (polarity): rho-bar per channel, paired shift vs A")
        rep["gain_sweep"] = {}
        # Matched seeds across gains, for the same reason as the rule-form
        # table: g=0.8 was deepened to 100 seeds for H7 and the sweep arms
        # were not, so an unmatched comparison would confound gain with n.
        gmax = min(len({r["seed"] for r in allrows
                        if r.get("gain", GAIN) == gv
                        and r["mode"] == "polarity" and r["cond"] == "A"
                        and r.get("rule", "corrective") == "corrective"})
                   for gv in gains)
        print(f"  (matched at {gmax} seeds per gain)")
        for gval in gains:
            sub = [r for r in allrows if r.get("gain", GAIN) == gval
                   and r["mode"] == "polarity" and r["seed"] <= gmax
                   and r.get("rule", "corrective") == "corrective"]
            for cond, _ in CONDITIONS[2:]:
                if not any(r["cond"] == cond for r in sub):
                    continue
                cells = {}
                for k in POLARITY_KEYS:
                    st = paired([{**r, "w": (r.get("W_final") or {}).get(k)}
                                 for r in sub], "w", cond, "polarity")
                    if st:
                        cells[k] = st
                if cells:
                    rep["gain_sweep"].setdefault(str(gval), {})[cond] = cells
                    print(f"  g={gval:<4} {cond}: " + "  ".join(
                        f"{k} {v['median_diff']:+.3f}"
                        f"{'*' if v['p'] < 0.05 else ' '}"
                        for k, v in cells.items()))

    rules = sorted({r.get("rule", "corrective") for r in allrows
                    if r["mode"] == "polarity"})
    if len(rules) > 1:
        print("\nRULE FORM (polarity): does 'disengage, never invert' survive "
              "swapping the underlying rule?")
        rep["rule_form"] = {}
        # Matched seeds across arms: the corrective arm was deepened to 100
        # seeds for H7, so comparing it raw against a 20-seed conformist arm
        # would be a seed-count difference dressed as a rule-form difference.
        nmax = min(len({r["seed"] for r in allrows
                        if r.get("rule", "corrective") == rl
                        and r["mode"] == "polarity"
                        and r.get("gain", GAIN) == GAIN and r["cond"] == "A"})
                   for rl in rules)
        print(f"  (matched at {nmax} seeds per arm)")
        for rl in rules:
            sub = [r for r in allrows if r.get("rule", "corrective") == rl
                   and r["mode"] == "polarity"
                   and r.get("gain", GAIN) == GAIN and r["seed"] <= nmax]
            for cond, _ in CONDITIONS[2:]:
                if not any(r["cond"] == cond for r in sub):
                    continue
                lv, cells = {}, {}
                for k in POLARITY_KEYS:
                    vals = [r["W_final"][k] for r in sub
                            if r["cond"] == cond and r.get("W_final")]
                    st = paired([{**r, "w": (r.get("W_final") or {}).get(k)}
                                 for r in sub], "w", cond, "polarity")
                    if vals and st:
                        lv[k] = float(np.median(vals))
                        cells[k] = st
                if cells:
                    rep["rule_form"].setdefault(rl, {})[cond] = {
                        "rho_bar": lv, "vs_A": cells}
                    print(f"  {rl:10s} {cond}: " + "  ".join(
                        f"{k} {lv[k]:+.3f}"
                        f"{'*' if cells[k]['p'] < 0.05 else ' '}"
                        for k in POLARITY_KEYS))
        print("  (minimum rho-bar anywhere: "
              f"{min(v['rho_bar'][k] for d in rep['rule_form'].values() for v in d.values() for k in v['rho_bar']):+.3f})")

    dest = os.path.join(OUT, "policy_report.json")
    with open(dest, "w") as f:
        json.dump(rep, f, indent=1)
    print(f"\nwrote {dest}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--merge", action="store_true")
    ap.add_argument("--analyze", action="store_true")
    ap.add_argument("--mode", default=None, choices=MODES)
    ap.add_argument("--checkpoint", default="runs.jsonl")
    ap.add_argument("--gain", type=float, default=GAIN)
    ap.add_argument("--response-mode", default="corrective",
                    choices=["corrective", "conformist"])
    ap.add_argument("--seeds", type=int, default=SEEDS)
    ap.add_argument("--conditions", default=None,
                    help="comma list, e.g. A,C,F,N (B is identical to A)")
    a = ap.parse_args()
    if a.run:
        run(a.mode, a.checkpoint, a.gain, a.response_mode, a.seeds,
            a.conditions.split(",") if a.conditions else None)
    elif a.merge:
        merge()
    elif a.analyze:
        analyze()
    else:
        ap.print_help()
