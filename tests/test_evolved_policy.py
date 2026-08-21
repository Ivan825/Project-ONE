"""Acceptance criteria for the v2 heritable response policy.

The v2 architecture (docs/PAPER2_PLAN.md) replaces the hand-written map from
self-model to action with a heritable per-agent weight matrix. Its first
obligation is to leave the published paper alone: with policy_mode="fixed",
every v1 trajectory, hash and RNG draw must be bit-identical. These tests are
the acceptance criterion for that, plus the invariants v2 itself needs.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from project_one import Config, Simulation                       # noqa: E402
from project_one.agents import (POLARITY_KEYS, POLICY_ACTIONS,  # noqa: E402
                                POLICY_FEATURES, POLICY_KEYS,
                                policy_features)
from project_one.feedback import BROADCAST_KEYS                   # noqa: E402


def _sim(seed=5, steps=400, **kw):
    cfg = Config(steps=steps, initial_population=80, snapshot_interval=0, **kw)
    s = Simulation(cfg, seed=seed)
    s.run()
    return s


# --- the v1 guarantee ------------------------------------------------------

def test_fixed_mode_is_the_default():
    assert Config().policy_mode == "fixed"


def test_fixed_mode_consumes_no_policy_rng():
    """The policy draws must sit behind the flag, or every stored v1 hash
    shifts. Comparing a fixed-mode run against one whose policy parameters are
    changed catches any draw that leaked out from behind the flag."""
    a = _sim(condition="F", distortion="invert")
    b = _sim(condition="F", distortion="invert",
             policy_init_sd=0.9, policy_mutation_sd=0.4)
    assert a.state_hash() == b.state_hash()


def test_fixed_mode_agents_carry_no_policy():
    s = _sim(condition="C")
    assert all(a.policy is None for a in s.agents.values())
    assert "mean_policy" not in s.global_memory[-1]


# --- v2 invariants ---------------------------------------------------------

def test_evolved_mode_is_deterministic():
    for cond in ("A", "C", "F", "N"):
        h = [_sim(condition=cond, distortion="invert",
                  policy_mode="evolved").state_hash() for _ in range(2)]
        assert h[0] == h[1], cond


def test_policy_is_in_the_state_hash():
    """A replay check that cannot see the policy would not be checking the
    thing v2 is about."""
    s = _sim(condition="C", policy_mode="evolved")
    h0 = s.state_hash()
    a = next(a for a in s.agents.values() if a.alive and a.policy)
    a.policy[POLICY_KEYS[0]] += 0.5
    assert s.state_hash() != h0


def test_policy_is_heritable_and_mutated():
    s = _sim(condition="C", steps=800, policy_mode="evolved")
    kids = [a for a in s.agents.values() if a.parent_id is not None and a.policy]
    assert kids, "no offspring produced; raise steps"
    kid = kids[0]
    parent = s.agents[kid.parent_id]
    assert set(kid.policy) == set(POLICY_KEYS)
    assert kid.policy != parent.policy            # mutated
    close = sum(abs(kid.policy[k] - parent.policy[k]) < 0.25 for k in POLICY_KEYS)
    assert close > 0.8 * len(POLICY_KEYS)         # but inherited, not redrawn


def test_policy_weights_allow_inversion():
    """Clamping to [0,1] would decide in advance that a population may only
    amplify a response, never invert it -- which is half the question."""
    s = _sim(condition="F", distortion="invert", steps=800,
             policy_mode="evolved", policy_init_sd=0.9)
    vals = [v for a in s.agents.values() if a.policy for v in a.policy.values()]
    assert min(vals) < -0.1 and max(vals) > 0.1
    assert min(vals) >= -1.0 and max(vals) <= 1.0


def test_policy_never_reaches_the_broadcast():
    """The evolved policy is measured, never transmitted: it must not appear
    in anything agents receive."""
    s = _sim(condition="C", policy_mode="evolved")
    for b in s.broadcast_memory:
        if b is not None:
            assert set(b) == set(BROADCAST_KEYS)


def test_feature_basis_is_centered_and_spans_both_rules():
    """An uncentered basis would make 'no policy' and 'no opinion' different
    things, and a mean shift would read as a learned response."""
    neutral = {k: 0.5 for k in BROADCAST_KEYS}
    phi = policy_features(neutral)
    assert phi["bias"] == 1.0
    for c in BROADCAST_KEYS:
        assert abs(phi[f"lin|{c}"]) < 1e-12
    assert len(POLICY_FEATURES) == 1 + 3 * len(BROADCAST_KEYS)
    assert len(POLICY_KEYS) == len(POLICY_ACTIONS) * len(POLICY_FEATURES)


def test_evolved_diverges_from_fixed():
    """If the flag changed nothing observable it would not be testing anything."""
    a = _sim(condition="C", steps=600)
    b = _sim(condition="C", steps=600, policy_mode="evolved")
    assert a.state_hash() != b.state_hash()


def test_condition_a_is_the_policy_null():
    """With no broadcast the policy is invisible to selection, so whatever
    movement condition A shows is drift. The measurement must still be taken
    there -- it is the reference every policy result is read against."""
    s = _sim(condition="A", steps=800, policy_mode="evolved")
    logged = [x for x in s.global_memory if "policy_norm" in x]
    assert len(logged) > 10
    assert any("mean_policy" in x for x in s.global_memory)
    assert s.global_memory[-1]["lineage_effective_n"] >= 1.0


# --- policy_mode="polarity": the low-dimensional design --------------------

def test_polarity_at_rho_one_is_exactly_the_hand_written_rule():
    """The strongest form of the answer to 'your rules are hand-written': the
    hand-written rule is not merely IN the searched space, it is a point in it
    that the engine reproduces BIT-IDENTICALLY. Verified, not argued."""
    keys = ("population", "mean_degree", "cooperation", "fragmentation",
            "inequality", "turnover", "mean_trait_global_sensitivity")

    def traj(**kw):
        s = _sim(condition="C", steps=800, **kw)
        return [tuple(round(x.get(k, 0.0), 12) for k in keys)
                for x in s.global_memory]

    frozen = dict(policy_mode="polarity", polarity_init_sd=0.0,
                  polarity_mutation_sd=0.0)
    assert traj(**frozen) == traj()


def test_polarity_at_rho_one_matches_the_conformist_rule_too():
    """Not just the default rule form: polarity scales whichever response_mode
    is in force, so both of Paper 1's hand-written rules are points in it."""
    keys = ("population", "cooperation", "fragmentation")

    def traj(**kw):
        s = _sim(condition="C", steps=800, response_mode="conformist", **kw)
        return [tuple(round(x.get(k, 0.0), 12) for k in keys)
                for x in s.global_memory]

    assert traj(policy_mode="polarity", polarity_init_sd=0.0,
                polarity_mutation_sd=0.0) == traj()


def test_polarity_reaches_inversion_and_indifference():
    """rho must be able to reach 0 (ignore this channel) and go negative
    (invert the response), or the space would exclude the two answers that
    matter most."""
    s = _sim(condition="F", distortion="invert", steps=800,
             policy_mode="polarity", polarity_init_sd=1.0)
    vals = [v for a in s.agents.values() if a.policy for v in a.policy.values()]
    assert min(vals) < 0.0 < max(vals)
    assert min(vals) >= -2.0 and max(vals) <= 2.0


def test_polarity_is_four_dimensional():
    s = _sim(condition="C", steps=400, policy_mode="polarity")
    a = next(x for x in s.agents.values() if x.policy)
    assert set(a.policy) == set(POLARITY_KEYS) and len(a.policy) == 4
