"""Metric validation against constructed cases with known answers (M2)."""
import os
import sys

import networkx as nx

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from project_one.agents import Agent
from project_one.observer import compute_self_model, _gini


def _mk_agents(n, energy=10.0):
    return {
        i: Agent(id=i, generation=0, parent_id=None, birth_time=0,
                 traits={}, energy=energy, max_lifespan=100)
        for i in range(n)
    }


def test_fragmentation_two_equal_components():
    g = nx.Graph()
    g.add_edges_from((i, j) for i in range(10) for j in range(i + 1, 10))
    g.add_edges_from((i, j) for i in range(10, 20) for j in range(i + 1, 20))
    s = compute_self_model(1, g, _mk_agents(20), [])
    assert s["components"] == 2
    assert abs(s["fragmentation"] - 0.5) < 1e-9


def test_fragmentation_fully_connected_is_zero():
    g = nx.complete_graph(20)
    s = compute_self_model(1, g, _mk_agents(20), [])
    assert s["components"] == 1
    assert s["fragmentation"] == 0.0


def test_centralization_star_exceeds_ring():
    star = nx.star_graph(19)          # node 0 connected to 19 others
    ring = nx.cycle_graph(20)
    s_star = compute_self_model(1, star, _mk_agents(20), [])
    s_ring = compute_self_model(1, ring, _mk_agents(20), [])
    assert s_star["centralization"] > 3 * s_ring["centralization"]
    assert abs(s_star["centralization"] - 0.5) < 1e-9   # 19 / (2*19)


def test_gini_bounds():
    assert _gini([5.0] * 50) < 1e-9                    # perfect equality
    assert _gini([0.0] * 49 + [100.0]) > 0.9           # near-total concentration
    assert _gini([]) == 0.0


def test_cooperation_rate_counts_shares():
    g = nx.empty_graph(10)
    events = [{"type": "share"}] * 4 + [{"type": "harvest"}] * 20
    s = compute_self_model(1, g, _mk_agents(10), events)
    assert abs(s["cooperation"] - 0.4) < 1e-9


def test_turnover_counts_births_and_deaths():
    g = nx.empty_graph(10)
    events = [{"type": "birth"}] * 3 + [{"type": "death"}] * 2
    s = compute_self_model(1, g, _mk_agents(10), events)
    assert abs(s["turnover"] - 0.5) < 1e-9


def test_inequality_reflects_energy_distribution():
    g = nx.empty_graph(10)
    equal = compute_self_model(1, g, _mk_agents(10, energy=10.0), [])
    agents = _mk_agents(10, energy=1.0)
    agents[0].energy = 1000.0
    unequal = compute_self_model(1, g, agents, [])
    assert unequal["inequality"] > equal["inequality"] + 0.5
