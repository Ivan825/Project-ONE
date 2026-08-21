"""Manifestations: transparent trait-vector agents.

v1 (the Complex Networks 2026 paper) gives every agent the SAME hand-written
map from a received self-model to action propensities, scaled by the heritable
trait ``global_sensitivity``.  v2 adds an optional *heritable response policy*
so that map is selected rather than specified -- see docs/PAPER2_PLAN.md.  The
policy is inert unless ``Config.policy_mode == "evolved"``, and consumes no RNG
draws when inert, so every v1 state hash reproduces bit-for-bit.
"""
from __future__ import annotations

from dataclasses import dataclass, field

TRAITS = ("cooperation", "exploration", "risk", "sociability", "sharing", "global_sensitivity")

# --- heritable response policy (policy_mode="evolved") ---------------------
# Rows: the action channels the fixed rules of v1 modify.  "reproduce" and
# "idle" are deliberately excluded, exactly as in v1, so feedback still adds
# mass only to non-reproductive actions and the reproduction-neutral control
# transfers unchanged.
POLICY_ACTIONS = ("connect", "harvest", "prune", "share")
# Columns: a uniform piecewise-linear basis over the five broadcast
# components -- a constant, the centered level, and two kinks at fixed knots.
# Uniform by design: per-feature knots tuned to our own rules would reinstate
# the designer choice this architecture exists to remove.  Both v1 rule forms
# lie inside the span (see docs/PAPER2_PLAN.md).
POLICY_COMPONENTS = ("centralization", "cooperation", "fragmentation",
                     "inequality", "turnover")
POLICY_KNOTS = (0.3, 0.6)


def policy_feature_names() -> tuple:
    names = ["bias"]
    for c in POLICY_COMPONENTS:
        names.append(f"lin|{c}")
        for th in POLICY_KNOTS:
            names.append(f"hin{th}|{c}")
    return tuple(names)


POLICY_FEATURES = policy_feature_names()
POLICY_KEYS = tuple(f"{a}~{f}" for a in POLICY_ACTIONS for f in POLICY_FEATURES)

# --- policy_mode="polarity": the low-dimensional design --------------------
# The 64-cell space above is not searchable by selection in this ecology --
# measured, not assumed: campaigns/policy_campaign shows selection on it is
# below the detection floor while the same estimator reads S(risk) = +0.011.
# So instead of letting agents invent a response rule coefficient by
# coefficient, let selection choose the POLARITY AND STRENGTH of the response
# on each action channel:
#
#     w[a] += rho_i[a] * (the hand-written rule's own term for a)
#
# rho = 1 recovers the hand-written rule exactly (bit-identically: multiplying
# by 1.0 is exact in IEEE-754 and the summation order is unchanged), rho = 0
# ignores the broadcast on that channel, and rho < 0 inverts the response.
# Four heritable numbers instead of 64, so the per-parameter fitness effect is
# orders of magnitude larger -- and the hand-written rule becomes one point in
# a space that contains indifference and inversion.
POLARITY_KEYS = POLICY_ACTIONS
POLARITY_LIMIT = 2.0


def policy_features(bc: dict) -> dict:
    """Fixed basis over a received broadcast.  Levels are centered so that a
    zero policy and an indifferent policy are the same thing -- otherwise a
    mean shift would read as a learned response."""
    out = {"bias": 1.0}
    for c in POLICY_COMPONENTS:
        v = float(bc.get(c, 0.0))
        out[f"lin|{c}"] = v - 0.5
        for th in POLICY_KNOTS:
            out[f"hin{th}|{c}"] = max(0.0, v - th)
    return out


@dataclass
class Agent:
    id: int
    generation: int
    parent_id: int | None
    birth_time: int
    traits: dict
    energy: float
    max_lifespan: int
    age: int = 0
    death_time: int | None = None
    cause_of_death: str | None = None
    offspring_count: int = 0
    received_global: dict | None = None   # last broadcast the agent has seen
    memory: list = field(default_factory=list)  # bounded local memory of events
    policy: dict | None = None            # heritable W, only under policy_mode="evolved"
    lineage_root: int | None = None       # founder this agent descends from

    MEMORY_CAP = 20

    def remember(self, item) -> None:
        self.memory.append(item)
        if len(self.memory) > self.MEMORY_CAP:
            self.memory.pop(0)

    @property
    def alive(self) -> bool:
        return self.death_time is None


def spawn_initial(rng, cfg, agent_id: int, t: int, prng=None) -> Agent:
    traits = {
        k: _clamp(rng.gauss(cfg.trait_means[k], cfg.trait_sd)) for k in TRAITS
    }
    lifespan = max(50, int(rng.gauss(cfg.max_lifespan_mean, cfg.max_lifespan_sd)))
    # Stagger initial ages: a synchronized founding cohort otherwise dies in
    # waves (mass old-age die-offs) that can extinguish the population.
    age = rng.randint(0, lifespan // 2)
    agent = Agent(
        id=agent_id, generation=0, parent_id=None, birth_time=t,
        traits=traits, energy=cfg.initial_energy * (0.5 + rng.random()),
        max_lifespan=lifespan, age=age,
    )
    agent.lineage_root = agent_id
    # Drawn from the DEDICATED policy stream, never the behavioral one, so
    # switching policy_mode does not perturb any behavioral draw. Under
    # policy_mode="fixed" nothing is drawn at all and v1 is byte-identical.
    mode = getattr(cfg, "policy_mode", "fixed")
    if mode in ("evolved", "polarity"):
        pr = prng if prng is not None else rng
        if mode == "polarity":
            # Centered on 1.0 -- the hand-written rule -- so the question is
            # whether selection moves the population AWAY from it, not whether
            # it can find it from nowhere.
            agent.policy = {k: _clamp_p(pr.gauss(1.0, cfg.polarity_init_sd))
                            for k in POLARITY_KEYS}
        else:
            agent.policy = {k: _clamp_w(pr.gauss(0.0, cfg.policy_init_sd))
                            for k in POLICY_KEYS}
    return agent


def spawn_child(rng, cfg, agent_id: int, parent: Agent, t: int,
                prng=None) -> Agent:
    traits = {
        k: _clamp(rng.gauss(parent.traits[k], cfg.mutation_sd)) for k in TRAITS
    }
    child = Agent(
        id=agent_id, generation=parent.generation + 1, parent_id=parent.id,
        birth_time=t, traits=traits, energy=cfg.reproduce_cost * 0.8,
        max_lifespan=max(50, int(rng.gauss(cfg.max_lifespan_mean, cfg.max_lifespan_sd))),
    )
    child.lineage_root = parent.lineage_root if parent.lineage_root is not None else parent.id
    mode = getattr(cfg, "policy_mode", "fixed")
    if mode in ("evolved", "polarity") and parent.policy:
        pr = prng if prng is not None else rng
        if mode == "polarity":
            child.policy = {
                k: _clamp_p(pr.gauss(parent.policy[k], cfg.polarity_mutation_sd))
                for k in POLARITY_KEYS
            }
        else:
            child.policy = {
                k: _clamp_w(pr.gauss(parent.policy[k], cfg.policy_mutation_sd))
                for k in POLICY_KEYS
            }
    return child


def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def _clamp_p(x: float) -> float:
    """Polarity is clamped symmetrically about zero, so inverting a response is
    exactly as reachable as doubling it."""
    return max(-POLARITY_LIMIT, min(POLARITY_LIMIT, x))


def _clamp_w(x: float) -> float:
    """Policy weights are clamped symmetrically: inverting a response must be
    as reachable as amplifying it, or the architecture would pre-judge which
    way a population is allowed to react to a lie."""
    return max(-1.0, min(1.0, x))
