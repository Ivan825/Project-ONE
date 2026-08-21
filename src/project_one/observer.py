"""The global observer: compresses the macrostate into the self-model S(t).

The observer MEASURES; it never commands. What agents see of S(t) is decided
by the feedback module according to the experimental condition.
"""
from __future__ import annotations

import networkx as nx


def compute_self_model(t: int, graph: nx.Graph, agents: dict, recent_events: list,
                       policy_full: bool = False) -> dict:
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

    # Freeman degree centralization: sum of (max_deg - deg_i) over the maximum
    # possible sum (n-1)(n-2); 1.0 for a star, 0.0 for any regular graph.
    if n > 2 and degs:
        dmax = max(degs)
        s["freeman_centralization"] = sum(dmax - d for d in degs) / ((n - 1) * (n - 2))
    else:
        s["freeman_centralization"] = 0.0

    # Betweenness concentration: share of total betweenness held by the
    # top-5% nodes (exact computation; population sizes here keep it cheap).
    if n > 2 and graph.number_of_edges() > 0:
        bc = nx.betweenness_centrality(graph, normalized=False)
        total = sum(bc.values())
        if total > 0:
            k = max(1, n // 20)
            top_bc = sorted(bc.values(), reverse=True)[:k]
            s["betweenness_concentration"] = sum(top_bc) / total
        else:
            s["betweenness_concentration"] = 0.0
    else:
        s["betweenness_concentration"] = 0.0

    # Cooperation rate: costly-helping events per living agent in the window
    shares = sum(1 for e in recent_events if e["type"] == "share")
    s["cooperation"] = min(1.0, shares / n)

    # Inequality: Gini over energy
    s["inequality"] = _gini([a.energy for a in living])

    # Turnover: births+deaths per capita in the window
    births = sum(1 for e in recent_events if e["type"] == "birth")
    deaths = sum(1 for e in recent_events if e["type"] == "death")
    s["turnover"] = min(1.0, (births + deaths) / n)

    # Mean heritable traits of the living population (never broadcast; logged so
    # campaigns can measure whether attention to the self-model is selected
    # for or against — e.g. does false feedback breed distrust?).
    traited = [a.traits for a in living if a.traits]
    if traited:
        for k in ("global_sensitivity", "cooperation", "sharing"):
            vals = [t[k] for t in traited if k in t]
            if vals:
                s["mean_trait_" + k] = sum(vals) / len(vals)

    # Mean heritable response policy, when policies are evolved rather than
    # written (v2). Also never broadcast: this is how the campaign measures
    # which response rule selection actually favours under each broadcast
    # regime, instead of the rule being an assumption of the model.
    policied = [a.policy for a in living if a.policy]
    if policied:
        n_p = len(policied)
        mean_w = {}
        for k in policied[0]:
            mean_w[k] = sum(p[k] for p in policied) / n_p
        # A scalar companion: how far the average agent's policy sits from
        # indifference. NOTE this rises under condition A as well, where the
        # policy is invisible to selection because no broadcast exists -- that
        # rise is lineage drift, and it is why every policy result must be read
        # paired against A rather than as a level. See docs/PAPER2_PLAN.md.
        s["policy_norm"] = (sum(v * v for v in mean_w.values()) / len(mean_w)) ** 0.5
        # Lineage concentration: the effective number of surviving founder
        # lines, which sets how large that drift can be. Reported alongside so
        # drift is measured rather than assumed.
        roots = {}
        for a in living:
            if a.policy:
                roots[a.lineage_root] = roots.get(a.lineage_root, 0) + 1
        if roots:
            tot = sum(roots.values())
            s["lineage_effective_n"] = 1.0 / sum((c / tot) ** 2
                                                 for c in roots.values())
        # The full 64-cell mean is the expensive field; store it sparsely.
        if policy_full or t == 0:
            s["mean_policy"] = mean_w

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
