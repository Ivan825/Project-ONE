import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from project_one import Config, Simulation


def _hash_for(condition: str, seed: int, steps: int = 300) -> str:
    cfg = Config(condition=condition, steps=steps, initial_population=80)
    sim = Simulation(cfg, seed=seed)
    sim.run()
    return sim.state_hash()


def test_seed_replay_identical():
    for condition in ("A", "B", "C", "F", "N"):
        assert _hash_for(condition, 7) == _hash_for(condition, 7)


def test_different_seeds_differ():
    assert _hash_for("C", 1) != _hash_for("C", 2)


def test_conditions_diverge_from_same_seed():
    # Feedback must actually change the trajectory relative to no-feedback.
    assert _hash_for("A", 42) != _hash_for("C", 42)


def test_population_survives():
    cfg = Config(condition="A", steps=500, initial_population=100)
    sim = Simulation(cfg, seed=11)
    sim.run()
    assert sim.population() > 0
