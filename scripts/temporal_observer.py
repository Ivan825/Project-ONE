#!/usr/bin/env python3
"""Run the paper's own observer over a REAL temporal network.

This is step 8 of docs/PAPER2_PLAN.md, and it is deliberately the first piece
of the empirical half to be built: it needs no calibration, no intervention and
no resolution of anything else, yet it either supports the five-dimensional
self-model as an empirically reasonable compression or tells us the ranges are
wrong before anything is built on top of them.

THE POINT OF THE DESIGN. The real edge stream is not fed to a re-implementation
of the observer. It is fed to `project_one.observer.compute_self_model`, the
exact function the simulator uses, by wrapping each observation window in shim
objects that satisfy that function's interface. Fragmentation, centralization,
Freeman centralization, betweenness concentration, mean degree and the Gini are
therefore computed by identical code on both sides, so a simulated and an
empirical S(t) are comparable by construction rather than by argument.

THE MAPPING (docs/PAPER2_PLAN.md Sect. 3.3). Three of the five broadcast
components are defined over agent internals that a temporal network does not
contain, so each is given an explicit empirical counterpart. These are stated
here and must be stated in the paper; they are the semantic content of
"calibrating against real data", and hiding them in code would be the whole
problem.

    component        model                       empirical counterpart
    fragmentation    1 - largest_cc / n          identical (windowed contact graph)
    centralization   top-5% degree share         identical
    cooperation      costly-help events / n      directed interactions per active node
    inequality       Gini over energy            Gini over interaction count
    turnover         (births + deaths) / n       (activity onsets + cessations) / n

A node is "alive" between its first and last observed interaction. A fixed
roster is then simply an ecology with near-zero turnover -- which the model can
represent with long lifespans -- so the fixed-roster objection dissolves rather
than needing a special case. The honest caveat, which belongs in the paper: the
model's deaths are energetic and the data's are observational. The observer
sees the same quantity either way, but they are not the same event.

Usage:
    python scripts/temporal_observer.py DATA.txt --format snap --window 86400
    python scripts/temporal_observer.py --selftest
"""
import argparse
import gzip
import json
import os
import sys

import networkx as nx
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))
from project_one.observer import compute_self_model  # noqa: E402

BROADCAST_KEYS = ("fragmentation", "centralization", "cooperation",
                  "inequality", "turnover")


class _ShimAgent:
    """Minimal object satisfying the observer's agent interface.

    energy carries the node's interaction count, so the observer's Gini over
    energy becomes a Gini over activity. traits is empty and policy is None, so
    the observer skips its trait and policy aggregation blocks entirely.
    """
    __slots__ = ("energy", "death_time", "traits", "policy")

    def __init__(self, activity):
        self.energy = float(activity)
        self.death_time = None      # every shim in a window is "living"
        self.traits = {}
        self.policy = None

    @property
    def alive(self):
        return True


def load_edge_stream(path, fmt="snap"):
    """Return [(u, v, t)] sorted by t.

    snap:          "SRC DST UNIXTS"   (CollegeMsg, email-Eu-core-temporal)
    sociopatterns: "t i j"            (SocioPatterns contact traces)
    """
    opener = gzip.open if str(path).endswith(".gz") else open
    out = []
    with opener(path, "rt") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith(("#", "%")):
                continue
            parts = line.replace(",", " ").split()
            if len(parts) < 3:
                continue
            if fmt == "sociopatterns":
                t, u, v = parts[0], parts[1], parts[2]
            else:
                u, v, t = parts[0], parts[1], parts[2]
            out.append((str(u), str(v), int(float(t))))
    out.sort(key=lambda e: e[2])
    return out


def observe_stream(stream, window, min_active=3):
    """Windowed S(t) for a real temporal network, via the paper's observer.

    Activity spans are computed over the WHOLE stream first, so onset and
    cessation are properties of the dataset rather than of the window grid.
    """
    if not stream:
        return []
    first_seen, last_seen = {}, {}
    for u, v, t in stream:
        for n in (u, v):
            first_seen.setdefault(n, t)
            last_seen[n] = t

    t0, t1 = stream[0][2], stream[-1][2]
    edges_by_window = {}
    for u, v, t in stream:
        edges_by_window.setdefault((t - t0) // window, []).append((u, v, t))

    out = []
    for w in range(int((t1 - t0) // window) + 1):
        chunk = edges_by_window.get(w, [])
        if not chunk:
            continue
        w_lo, w_hi = t0 + w * window, t0 + (w + 1) * window

        g = nx.Graph()
        activity = {}
        for u, v, _ in chunk:
            if u != v:
                g.add_edge(u, v)
            activity[u] = activity.get(u, 0) + 1
            activity[v] = activity.get(v, 0) + 1
        g.add_nodes_from(activity)
        if len(activity) < min_active:
            continue

        # cooperation <- one "share" per directed interaction;
        # turnover    <- one "birth" per onset, one "death" per cessation.
        events = [{"type": "share"} for _ in chunk]
        events += [{"type": "birth"} for n in activity
                   if w_lo <= first_seen[n] < w_hi]
        events += [{"type": "death"} for n in activity
                   if w_lo <= last_seen[n] < w_hi]

        agents = {n: _ShimAgent(c) for n, c in activity.items()}
        s = compute_self_model(w_lo, g, agents, events)
        s["window_index"] = w
        s["n_interactions"] = len(chunk)
        # HAZARD (found on synthetic data before any real dataset was loaded):
        # the observer caps cooperation and turnover at 1.0 because a BROADCAST
        # component must lie in [0,1]. As a CALIBRATION TARGET that cap is
        # poison -- a target pinned at its ceiling on both sides looks like a
        # perfect fit while carrying no information. The uncapped rates are
        # therefore kept alongside, and the fit must use these.
        s["cooperation_raw"] = len(chunk) / len(activity)
        s["turnover_raw"] = (sum(1 for n in activity if w_lo <= first_seen[n] < w_hi)
                             + sum(1 for n in activity
                                   if w_lo <= last_seen[n] < w_hi)) / len(activity)
        s["saturated"] = bool(s["cooperation_raw"] > 1.0 or s["turnover_raw"] > 1.0)
        out.append(s)
    return out


def window_sweep(stream, windows, min_active=3):
    """How each component depends on the observation window.

    The window is a free parameter that drives fragmentation directly (a wide
    window connects everything, a narrow one shatters it) and saturates
    cooperation. It must therefore be fixed in advance on stated grounds, like
    every other pre-registered choice -- never picked because a fit improved.
    This prints the evidence that choice should be made on.
    """
    print(f"  {'window':>10s} {'wins':>5s} {'frag':>7s} {'centr':>7s} "
          f"{'coop_raw':>9s} {'ineq':>7s} {'turn_raw':>9s} {'sat%':>5s}")
    rows = {}
    for w in windows:
        tr = observe_stream(stream, w, min_active)
        if not tr:
            continue
        med = lambda k: float(np.median([s[k] for s in tr if k in s]))
        sat = 100.0 * sum(s["saturated"] for s in tr) / len(tr)
        rows[w] = {"n_windows": len(tr), "fragmentation": med("fragmentation"),
                   "centralization": med("centralization"),
                   "cooperation_raw": med("cooperation_raw"),
                   "inequality": med("inequality"),
                   "turnover_raw": med("turnover_raw"), "pct_saturated": sat}
        print(f"  {w:10d} {len(tr):5d} {med('fragmentation'):7.3f} "
              f"{med('centralization'):7.3f} {med('cooperation_raw'):9.3f} "
              f"{med('inequality'):7.3f} {med('turnover_raw'):9.3f} {sat:5.0f}")
    return rows


def summarize(traj, label=""):
    rep = {"label": label, "n_windows": len(traj), "components": {}}
    print(f"\n{label}: {len(traj)} windows")
    print(f"  {'component':22s} {'min':>8s} {'median':>8s} {'max':>8s} "
          f"{'sd':>8s}")
    for k in BROADCAST_KEYS:
        v = np.array([s[k] for s in traj if k in s], float)
        if not len(v):
            continue
        rep["components"][k] = {"min": float(v.min()), "median": float(np.median(v)),
                                "max": float(v.max()), "sd": float(v.std())}
        print(f"  {k:22s} {v.min():8.3f} {np.median(v):8.3f} {v.max():8.3f} "
              f"{v.std():8.3f}")
    # Is the self-model actually VARIABLE in real networks, and are its
    # components independent enough for a five-dimensional broadcast to be
    # carrying five things rather than one?
    mat = np.array([[s[k] for k in BROADCAST_KEYS] for s in traj], float)
    if len(mat) > 2:
        c = np.corrcoef(mat.T)
        rep["correlations"] = {f"{a}~{b}": float(c[i, j])
                               for i, a in enumerate(BROADCAST_KEYS)
                               for j, b in enumerate(BROADCAST_KEYS) if i < j}
        print("  strongest component correlations:")
        for k, val in sorted(rep["correlations"].items(),
                             key=lambda kv: -abs(kv[1]))[:4]:
            print(f"    {k:46s} {val:+.2f}")
    return rep


# --- self-test: hand-computable cases, no external data needed -------------

def _selftest():
    ok = True

    def check(name, got, want, tol=1e-9):
        nonlocal ok
        good = abs(got - want) < tol
        ok &= good
        print(f"  {'OK  ' if good else 'FAIL'} {name}: got {got:.4f}, want {want:.4f}")

    # Two disjoint triangles in one window: 6 nodes, largest component 3.
    W = 100
    stream = [("a", "b", 1), ("b", "c", 2), ("a", "c", 3),
              ("d", "e", 4), ("e", "f", 5), ("d", "f", 6)]
    tr = observe_stream(stream, W)
    print("two disjoint triangles, single window:")
    check("fragmentation = 1 - 3/6", tr[0]["fragmentation"], 0.5)
    check("mean_degree = 2*6/6", tr[0]["mean_degree"], 2.0)
    # every node's first AND last interaction is in this window -> 12 events/6
    check("turnover = (6 onsets + 6 cessations)/6", tr[0]["turnover"], 1.0)
    check("cooperation = 6 interactions/6 nodes", tr[0]["cooperation"], 1.0)
    # all six nodes have identical activity -> Gini 0
    check("inequality = 0 (uniform activity)", tr[0]["inequality"], 0.0)

    # A star: one hub, four leaves. Connected, so fragmentation 0.
    stream = [("h", x, i) for i, x in enumerate("wxyz", start=1)]
    tr = observe_stream(stream, W)
    print("star with four leaves:")
    check("fragmentation = 0", tr[0]["fragmentation"], 0.0)
    check("mean_degree = 2*4/5", tr[0]["mean_degree"], 1.6)
    # Freeman centralization of a star is exactly 1
    check("freeman_centralization = 1", tr[0]["freeman_centralization"], 1.0)

    # Two windows: onset/cessation must be dataset-wide, not per-window.
    stream = [("a", "b", 1), ("a", "b", 150)]
    tr = observe_stream(stream, W, min_active=2)
    print("one persistent pair across two windows:")
    check("window 0 turnover = 2 onsets/2", tr[0]["turnover"], 1.0)
    check("window 1 turnover = 2 cessations/2", tr[1]["turnover"], 1.0)
    print(f"\nself-test: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("path", nargs="?")
    ap.add_argument("--format", default="snap",
                    choices=["snap", "sociopatterns"])
    ap.add_argument("--window", type=int, default=86400,
                    help="observation window in dataset time units (default 1 day)")
    ap.add_argument("--label", default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--sweep", action="store_true",
                    help="report component dependence on the observation window")
    a = ap.parse_args()
    if a.selftest:
        sys.exit(_selftest())
    if not a.path:
        ap.error("give a dataset path or --selftest")
    stream = load_edge_stream(a.path, a.format)
    label = a.label or os.path.basename(a.path)
    print(f"{label}: {len(stream)} timestamped edges, "
          f"{len({n for u, v, _ in stream for n in (u, v)})} nodes, "
          f"span {(stream[-1][2] - stream[0][2]) / 86400:.1f} days")
    if a.sweep:
        base = a.window
        window_sweep(stream, [base // 8, base // 4, base // 2, base,
                              base * 2, base * 4])
        sys.exit(0)
    traj = observe_stream(stream, a.window)
    rep = summarize(traj, label)
    if a.out:
        with open(a.out, "w") as f:
            json.dump({"summary": rep, "trajectory": traj}, f, indent=1)
        print(f"wrote {a.out}")
