"""Run configuration. Every run is fully determined by (Config, seed)."""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict


@dataclass
class Config:
    # Experimental condition: A, B, C, F, N  (see README / docs/PLAN.md)
    condition: str = "A"
    # For condition F: how the broadcast self-model is distorted.
    #   "invert"  - report the mirror image of each normalized metric
    #   "crisis"  - always report high fragmentation / low cooperation
    #   "utopia"  - always report low fragmentation / high cooperation
    distortion: str = "invert"

    # World
    steps: int = 2000
    initial_population: int = 150
    max_population: int = 1200
    initial_edges_per_agent: int = 3

    # Environment. Regeneration is density-dependent (logistic with a base trickle):
    #   regen(R) = resource_base_regen + resource_regen_rate * R * (1 - R / resource_capacity)
    # so a depleted pool recovers instead of trapping the population at subsistence.
    resource_capacity: float = 6000.0
    resource_base_regen: float = 60.0
    resource_regen_rate: float = 0.12
    harvest_rate: float = 2.5            # max energy an agent can harvest per step

    # Agent energetics
    initial_energy: float = 20.0
    metabolism: float = 0.8              # energy lost per step just living
    action_cost: float = 0.25
    share_amount: float = 3.0
    reproduce_threshold: float = 30.0
    reproduce_cost: float = 16.0
    min_reproduce_age: int = 15
    max_lifespan_mean: float = 400.0
    max_lifespan_sd: float = 80.0

    # Traits: mean of initial population distribution (each trait in [0,1])
    trait_means: dict = field(default_factory=lambda: {
        "cooperation": 0.5, "exploration": 0.5, "risk": 0.5,
        "sociability": 0.5, "sharing": 0.5, "global_sensitivity": 0.5,
    })
    trait_sd: float = 0.15
    mutation_sd: float = 0.05

    # Observer / feedback
    observer_interval: int = 10          # steps between S(t) computations
    feedback_gain: float = 0.8           # how strongly global signal shifts action propensities
    # How agents respond to the broadcast:
    #   "corrective"  - repair reported deficits (default)
    #   "conformist"  - imitate the reported norm
    response_mode: str = "corrective"
    # v2 (docs/PAPER2_PLAN.md). "fixed" reproduces the paper exactly: every
    # agent shares the hand-written response_mode map above. "evolved" replaces
    # that map with a heritable per-agent weight matrix W over a fixed
    # piecewise-linear basis (see agents.POLICY_KEYS), initialized N(0,
    # policy_init_sd), mutated at reproduction, clamped to [-1, 1] so that
    # inverting a response is as reachable as amplifying it. The two
    # hand-written rules then become two points in a space the population
    # searches, rather than the architecture's answer to its own question.
    # Inert and RNG-free unless switched on, so every v1 state hash is
    # preserved bit-for-bit.
    #   "polarity"  - four heritable scalars scaling the hand-written rule per
    #                  action channel; rho=1 IS the hand-written rule (exactly),
    #                  rho=0 ignores the broadcast there, rho<0 inverts it.
    policy_mode: str = "fixed"
    policy_init_sd: float = 0.3
    policy_mutation_sd: float = 0.05
    # The full 64-cell mean policy is bulky; store it this often (steps).
    # policy_norm and lineage_effective_n are logged every observer tick.
    policy_log_interval: int = 500
    polarity_init_sd: float = 0.5      # spread around rho = 1 at founding
    polarity_mutation_sd: float = 0.08
    # Robustness control for the evolutionary result. Feedback adds mass only to
    # non-reproductive actions, so after normalization a higher-gamma agent has a
    # mechanically LOWER probability of selecting "reproduce" whenever the
    # broadcast carries corrective drive. With reproduction_neutral=True the
    # reproduce weight is rescaled by (1 + D_i / N_0) -- D_i the feedback mass
    # added, N_0 the base non-reproductive mass -- which leaves P(reproduce)
    # exactly equal to its no-broadcast value while preserving the intended
    # feedback effect on the other actions. Isolates ecological selection on
    # global_sensitivity from the direct reproductive-opportunity cost.
    reproduction_neutral: bool = False
    # Second robustness control for the evolutionary result. Hub-targeted
    # pruning normally fires with probability gamma_i (NOT gamma_i * g), giving
    # receiver sensitivity a second, differently-scaled behavioral channel.
    # With pruning_gamma_free=True that probability is fixed at 0.5 for every
    # agent, removing gamma's influence on target selection while preserving
    # the mechanism itself and consuming the identical RNG draw.
    pruning_gamma_free: bool = False
    # Condition R: broadcast a replayed self-model trajectory (recorded from a
    # different seed's observed-but-blind run) — realistic structure, no
    # self-reference. List of per-tick broadcast dicts.
    replay_trajectory: list | None = None
    snapshot_interval: int = 50          # steps between stored network snapshots (0 disables)

    # Shock (disturbance experiment); step<=0 disables.
    # If shock_fraction > 0, that fraction of the living population (highest-
    # degree first) is removed; otherwise shock_hubs_removed fixed count.
    shock_step: int = 0
    shock_hubs_removed: int = 10
    shock_fraction: float = 0.0

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2, sort_keys=True)

    @classmethod
    def from_file(cls, path: str) -> "Config":
        with open(path) as f:
            data = json.load(f)
        cfg = cls()
        for k, v in data.items():
            if not hasattr(cfg, k):
                raise KeyError(f"Unknown config key: {k}")
            setattr(cfg, k, v)
        return cfg
