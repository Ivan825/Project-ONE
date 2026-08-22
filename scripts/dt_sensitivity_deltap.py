#!/usr/bin/env python3
"""Does the passive-counterfactual conclusion depend on observer cadence?

Reruns the harsh-shock protocol at observer_interval Delta-t in {5, 10, 20}
(10 is the paper's default), conditions A, F(invert), N, 30 paired seeds, and
computes Delta P = P_actual - P_passive at each cadence. R is excluded: replay
libraries are recorded on the default cadence and cannot be replayed onto a
different observer grid without resampling, which would test the resampler.

In-process: trajectories are consumed directly, nothing written to runs/.
"""
import importlib.util, json, os, sys
from concurrent.futures import ProcessPoolExecutor
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))
from project_one import Config, Simulation

spec = importlib.util.spec_from_file_location(
    "pnc", os.path.join(HERE, "passive_null_checks.py"))
pnc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pnc)
KEYS, pull_series, paired = pnc.KEYS, pnc.pull_series, pnc.paired

SEEDS = list(range(1, 31))

def run_one(job):
    dt, cond, seed = job
    cfg = Config(condition=cond, distortion="invert", steps=4000,
                 shock_step=2000, shock_fraction=0.4, feedback_gain=0.8,
                 observer_interval=dt, snapshot_interval=0)
    sim = Simulation(cfg, seed=seed)
    sim.run()
    return {"dt": dt, "cond": cond, "seed": seed,
            "globals": sim.global_memory,
            "broadcasts": sim.broadcast_memory}

def main():
    jobs = [(dt, c, s) for dt in (5, 10, 20) for c in ("A", "F", "N")
            for s in SEEDS]
    workers = max(1, os.cpu_count() or 2)
    print(f"{len(jobs)} runs on {workers} workers", flush=True)
    with ProcessPoolExecutor(max_workers=workers) as ex:
        rows = list(ex.map(run_one, jobs))
    by = {(r["dt"], r["cond"], r["seed"]): r for r in rows}

    out = {}
    for dt in (5, 10, 20):
        dF, dN = [], []
        rawF, rawN, pasF, pasN = [], [], [], []
        for s in SEEDS:
            A, F, N = by[(dt, "A", s)], by[(dt, "F", s)], by[(dt, "N", s)]
            aF = pull_series(F["globals"],
                             lambda i, st, bl=F["broadcasts"]:
                             bl[i] if i < len(bl) else None)
            pF = pull_series(A["globals"],
                             lambda i, st: {k: 1.0 - st[k] for k in KEYS})
            aN = pull_series(N["globals"],
                             lambda i, st, bl=N["broadcasts"]:
                             bl[i] if i < len(bl) else None)
            pN = pull_series(A["globals"],
                             lambda i, st, bl=N["broadcasts"]:
                             bl[i] if i < len(bl) else None)
            dF.append(aF - pF); dN.append(aN - pN)
            rawF.append(aF); rawN.append(aN); pasF.append(pF); pasN.append(pN)
        out[str(dt)] = {
            "raw_F_median": float(np.median(rawF)),
            "raw_N_median": float(np.median(rawN)),
            "passive_F_median": float(np.median(pasF)),
            "passive_N_median": float(np.median(pasN)),
            "delta_F_median": float(np.median(dF)),
            "delta_N_median": float(np.median(dN)),
            "F_vs0_p": paired(dF, [0.0] * len(dF))["wilcoxon_p"],
            "N_vs0_p": paired(dN, [0.0] * len(dN))["wilcoxon_p"],
            "diff_in_diff_F_vs_N_p": paired(dF, dN)["wilcoxon_p"],
        }
        o = out[str(dt)]
        print(f"dt={dt:2d}:  dP medians  F {o['delta_F_median']:+.4f}  "
              f"N {o['delta_N_median']:+.4f}   vs0 p: F {o['F_vs0_p']:.1e} "
              f"N {o['N_vs0_p']:.1e}   FvsN p {o['diff_in_diff_F_vs_N_p']:.3f}",
              flush=True)

    dest = os.path.join(ROOT, "campaigns", "dt_sensitivity_deltap.json")
    with open(dest, "w") as f:
        json.dump(out, f, indent=1)
    print("wrote", dest)

if __name__ == "__main__":
    main()
