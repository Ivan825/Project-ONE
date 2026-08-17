"""The global observer: compresses the macrostate into the self-model S(t).

The observer MEASURES; it never commands. What agents see of S(t) is decided
by the feedback module according to the experimental condition.
"""
from __future__ import annotations

import networkx as nx


def compute_self_model(t: int, graph: nx.Graph, agents: dict, recent_events: list) -> dict:
    """Return S(t): a small dict of normalized macroscopic measurements."""
    living = [a for a in agents.values() if a.alive]
    n = len(living)
    s = {"t": t, "population": n}

    if n == 0:
        s.update(fragmentation=1.0, centralization=0.0, cooperation=0.0,
                 inequality=0.0, mean_degree=0.0, turnover=0.0)
        return s

    # Connectivity / fragmentation
    comps = list(nx.connected_components(graph)) if graph.number_of_nodes() else []
    largest = max((len(c) for c in comps), default=0)
    s["components"] = len(comps)
    s["fragmentation"] = 1.0 - (largest / n) if n else 1.0
    degs = [d for _, d in graph.degree()]
    s["mean_degree"] = sum(degs) / n if n else 0.0

    # Centralization: share of edges touching the top-5% degree nodes
    if degs and graph.number_of_edges() > 0:
        k = max(1, n // 20)
        top = sorted(degs, reverse=True)[:k]
        s["centralization"] = min(1.0, sum(top) / (2.0 * graph.number_of_edges()))
    else:
        s["centralization"] = 0.0

    # Cooperation rate: costly-helping events per living agent in the window
    shares = sum(1 for e in recent_events if e["type"] == "share")
    s["cooperation"] = min(1.0, shares / n)

    # Inequality: Gini over energy
    s["inequality"] = _gini([a.energy for a in living])

    # Turnover: births+deaths per capita in the window
    births = sum(1 for e in recent_events if e["type"] == "birth")
    deaths = sum(1 for e in recent_events if e["type"] == "death")
    s["turnover"] = min(1.0, (births + deaths) / n)

    return s


def _gini(values: list) -> float:
    vals = sorted(max(0.0, v) for v in values)
    n = len(vals)
    total = sum(vals)
    if n == 0 or total == 0:
        return 0.0
    cum = 0.0
    for i, v in enumerate(vals, start=1):
        cum += i * v
    return max(0.0, min(1.0, (2.0 * cum) / (n * total) - (n + 1.0) / n))
