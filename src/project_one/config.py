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

    # Environment
    resource_capacity: float = 4000.0
    resource_regen: float = 120.0        # per step
    harvest_rate: float = 3.0            # max energy an agent can harvest per step

    # Agent energetics
    initial_energy: float = 20.0
    metabolism: float = 1.0              # energy lost per step just living
    action_cost: float = 0.25
    share_amount: float = 3.0
    reproduce_threshold: float = 40.0
    reproduce_cost: float = 22.0
    min_reproduce_age: int = 20
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

    # Shock (disturbance experiment); step<=0 disables
    shock_step: int = 0
    shock_hubs_removed: int = 10

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
