#!/usr/bin/env python3
"""Clustering nulls for the emergent network (both nulls quoted in Sect. 3.4).

Re-runs deterministic sims to t=2000, takes the giant component, and compares
its average clustering, path length and degree heterogeneity against:

  * an Erdos-Renyi G(n, m) null (20 draws) -- the conventional small-world
    reference, which does NOT preserve the degree sequence;
  * a degree-preserving configuration-model null (20 double-edge-swap
    randomizations, 10x|E| swaps each) -- strictly harder, since any
    clustering excess attributable to the degree sequence alone is removed.

Writes campaigns/network_structure_nulls.json.

    python scripts/config_model_null.py
"""
import json
import os
import statistics
import sys

import networkx as nx

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "src"))
from project_one import Config, Simulation  # noqa: E402


def degree_cv(g):
    d = [x for _, x in g.degree()]
    return statistics.pstdev(d) / statistics.fmean(d)


def main():
    rows = []
    for cond in ("A", "C"):
        for seed in (1, 2, 3):
            cfg = Config(condition=cond, steps=2000, snapshot_interval=0)
            sim = Simulation(cfg, seed=seed)
            sim.run()
            g = sim.graph
            gc = g.subgraph(max(nx.connected_components(g), key=len)).copy()
            n, m = gc.number_of_nodes(), gc.number_of_edges()
            c_obs = nx.average_clustering(gc)
            L = nx.average_shortest_path_length(gc)
            cv = degree_cv(gc)

            # Erdos-Renyi G(n, m): same size and density, degrees not preserved.
            er = [nx.average_clustering(nx.gnm_random_graph(n, m, seed=2000 + i))
                  for i in range(20)]
            c_er = statistics.fmean(er)
            r_er = c_obs / c_er if c_er > 0 else float("inf")

            # Configuration model: exact degree sequence preserved.
            cm = []
            for i in range(20):
                h = gc.copy()
                nx.double_edge_swap(h, nswap=10 * m, max_tries=200 * m,
                                    seed=1000 + i)
                cm.append(nx.average_clustering(h))
            c_cm = statistics.fmean(cm)
            r_cm = c_obs / c_cm if c_cm > 0 else float("inf")

            rows.append({"condition": cond, "seed": seed, "n": n, "m": m,
                         "C_obs": c_obs, "C_er": c_er, "ratio_er": r_er,
                         "C_config": c_cm, "ratio_config": r_cm,
                         "L": L, "degree_cv": cv})
            print(f"{cond} s{seed}: n={n} m={m} C_obs={c_obs:.4f} "
                  f"| ER {c_er:.4f} ratio={r_er:.2f} "
                  f"| config {c_cm:.4f} ratio={r_cm:.2f} "
                  f"| L={L:.2f} cv={cv:.3f}")

    def rng(key):
        v = [r[key] for r in rows]
        return {"min": min(v), "max": max(v), "mean": statistics.fmean(v)}

    out = {"per_graph": rows,
           "summary": {k: rng(k) for k in
                       ("ratio_er", "ratio_config", "L", "degree_cv")}}
    dest = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                        "campaigns", "network_structure_nulls.json")
    with open(dest, "w") as f:
        json.dump(out, f, indent=1)

    s = out["summary"]
    print(f"\nclustering ratio vs Erdos-Renyi null:      "
          f"{s['ratio_er']['min']:.2f}-{s['ratio_er']['max']:.2f} "
          f"(mean {s['ratio_er']['mean']:.2f})")
    print(f"clustering ratio vs degree-preserving null: "
          f"{s['ratio_config']['min']:.2f}-{s['ratio_config']['max']:.2f} "
          f"(mean {s['ratio_config']['mean']:.2f})")
    print(f"L: {s['L']['min']:.2f}-{s['L']['max']:.2f} | "
          f"degree CV: {s['degree_cv']['min']:.3f}-{s['degree_cv']['max']:.3f}")
    print(f"wrote {os.path.normpath(dest)}")


if __name__ == "__main__":
    main()
