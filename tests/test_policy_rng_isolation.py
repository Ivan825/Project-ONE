"""The policy stream must never perturb the behavioural stream.

Drawing 64 heritable weights per birth is a lot of random numbers. Taken from
the behavioural PRNG they shift every subsequent behavioural draw, so switching
policy_mode would change the trajectory even under condition A -- where no
broadcast exists and the policy therefore cannot affect a single decision. That
would silently confound every evolved-vs-fixed comparison the v2 design rests
on, so it gets its own test file.

Same failure mode, and the same fix, as the dedicated signal_rng stream: give
the policy its own stream.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from project_one import Config, Simulation                     # noqa: E402

BEHAVIOURAL = ("population", "mean_degree", "cooperation", "fragmentation",
               "inequality", "turnover", "centralization",
               "freeman_centralization", "betweenness_concentration",
               "mean_trait_global_sensitivity", "mean_trait_cooperation",
               "mean_trait_sharing")


def _trajectory(mode, condition="A", seed=9, steps=1200):
    cfg = Config(condition=condition, steps=steps, shock_step=steps // 2,
                 shock_fraction=0.4, policy_mode=mode, snapshot_interval=0)
    sim = Simulation(cfg, seed=seed)
    sim.run()
    return [tuple(round(s.get(k, 0.0), 12) for k in BEHAVIOURAL)
            for s in sim.global_memory]


def test_policy_mode_cannot_change_a_silent_world():
    """Condition A broadcasts nothing, so the policy is causally inert there.
    Turning it on must therefore change nothing observable."""
    assert _trajectory("fixed") == _trajectory("evolved")


def test_policy_mode_cannot_change_an_observed_but_blind_world():
    """Condition B runs the observer but tells the agents nothing, so the
    policy is inert there too."""
    assert _trajectory("fixed", condition="B") == _trajectory("evolved",
                                                              condition="B")


def test_policy_parameters_do_not_move_a_silent_world():
    """Not just the on/off switch: the policy's own parameters must not leak
    into behaviour when no broadcast exists."""
    a = _trajectory("evolved")
    cfg = Config(condition="A", steps=1200, shock_step=600, shock_fraction=0.4,
                 policy_mode="evolved", policy_init_sd=0.9,
                 policy_mutation_sd=0.4, snapshot_interval=0)
    sim = Simulation(cfg, seed=9)
    sim.run()
    b = [tuple(round(s.get(k, 0.0), 12) for k in BEHAVIOURAL)
         for s in sim.global_memory]
    assert a == b


def test_polarity_mode_is_also_rng_isolated():
    """The four-scalar variant draws from the same dedicated stream."""
    assert _trajectory("fixed") == _trajectory("polarity")


def test_policy_does_change_a_world_that_receives_a_broadcast():
    """The counterpart: where a broadcast exists, the policy MUST matter, or
    the three tests above would be passing for the wrong reason."""
    assert _trajectory("fixed", condition="C") != _trajectory("evolved",
                                                              condition="C")
