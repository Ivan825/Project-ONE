"""Manifestations: transparent trait-vector agents (no learned policies in v1)."""
from __future__ import annotations

from dataclasses import dataclass, field

TRAITS = ("cooperation", "exploration", "risk", "sociability", "sharing", "global_sensitivity")


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

    MEMORY_CAP = 20

    def remember(self, item) -> None:
        self.memory.append(item)
        if len(self.memory) > self.MEMORY_CAP:
            self.memory.pop(0)

    @property
    def alive(self) -> bool:
        return self.death_time is None


def spawn_initial(rng, cfg, agent_id: int, t: int) -> Agent:
    traits = {
        k: _clamp(rng.gauss(cfg.trait_means[k], cfg.trait_sd)) for k in TRAITS
    }
    lifespan = max(50, int(rng.gauss(cfg.max_lifespan_mean, cfg.max_lifespan_sd)))
    # Stagger initial ages: a synchronized founding cohort otherwise dies in
    # waves (mass old-age die-offs) that can extinguish the population.
    age = rng.randint(0, lifespan // 2)
    return Agent(
        id=agent_id, generation=0, parent_id=None, birth_time=t,
        traits=traits, energy=cfg.initial_energy * (0.5 + rng.random()),
        max_lifespan=lifespan, age=age,
    )


def spawn_child(rng, cfg, agent_id: int, parent: Agent, t: int) -> Agent:
    traits = {
        k: _clamp(rng.gauss(parent.traits[k], cfg.mutation_sd)) for k in TRAITS
    }
    return Agent(
        id=agent_id, generation=parent.generation + 1, parent_id=parent.id,
        birth_time=t, traits=traits, energy=cfg.reproduce_cost * 0.8,
        max_lifespan=max(50, int(rng.gauss(cfg.max_lifespan_mean, cfg.max_lifespan_sd))),
    )


def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))
