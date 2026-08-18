#!/usr/bin/env python3
"""Degree-preserving (configuration-model) clustering null for the emergent
network. Re-runs deterministic sims to t=2000, takes the giant component, and
compares its average clustering against 20 degree-preserving randomizations
(double edge swaps, 10x|E| swaps each) — a stricter null than Erdos-Renyi
because it keeps the exact degree sequence.

    python scripts/config_model_null.py
"""
import os
import statistics
import sys

import networkx as nx

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "src"))
from project_one import Config, Simulation  # noqa: E402


def main():
    rows = []
    for cond in ("A", "C"):
        for seed in (1, 2, 3):
            cfg = Config(condition=cond, steps=2000, snapshot_interval=0)
            sim = Simulation(cfg, seed=seed)
            sim.run()
            g = sim.graph
            gc = g.subgraph(max(nx.connected_components(g), key=len)).copy()
            c_obs = nx.average_clustering(gc)
            L = nx.average_shortest_path_length(gc)
            nulls = []
            for i in range(20):
                h = gc.copy()
                nx.double_edge_swap(h, nswap=10 * h.number_of_edges(),
                                    max_tries=200 * h.number_of_edges(),
                                    seed=1000 + i)
                nulls.append(nx.average_clustering(h))
            c_null = statistics.mean(nulls)
            ratio = c_obs / c_null if c_null > 0 else float("inf")
            rows.append((cond, seed, gc.number_of_nodes(), gc.number_of_edges(),
                         c_obs, c_null, ratio, L))
            print(f"{cond} s{seed}: n={gc.number_of_nodes()} m={gc.number_of_edges()} "
                  f"C_obs={c_obs:.4f} C_null={c_null:.4f} ratio={ratio:.2f} L={L:.2f}")
    ratios = [r[6] for r in rows]
    print(f"\nclustering ratio vs degree-preserving null: "
          f"min={min(ratios):.2f} max={max(ratios):.2f} "
          f"mean={statistics.mean(ratios):.2f}")


if __name__ == "__main__":
    main()
