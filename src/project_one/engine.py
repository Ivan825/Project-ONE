"""Core simulation engine (M0/M1).

Deterministic given (Config, seed): one behavioral random.Random drives every
agent choice, and a separate dedicated stream (signal_rng) generates
stochastic broadcast signals, so constructing the noise signal never advances
the behavioral PRNG. Agents are iterated in sorted-id order, and all neighbor
sampling sorts first.
"""
from __future__ import annotations

import hashlib
import json
import os
import random

import networkx as nx

from .agents import Agent, spawn_initial, spawn_child
from .config import Config
from .feedback import make_broadcast
from .observer import compute_self_model


class Simulation:
    def __init__(self, cfg: Config, seed: int):
        self.cfg = cfg
        self.seed = seed
        self.rng = random.Random(seed)
        # Dedicated stream for broadcast-signal generation (condition N).
        # Keeping signal generation off the behavioral stream guarantees that
        # constructing the noise signal never perturbs subsequent behavioral
        # draws, so constructing the noise signal never advances this stream.
        # Conditions that draw nothing from this stream are bit-identical to
        # the single-stream implementation.
        self.signal_rng = random.Random(1_000_003 * seed + 12345)
        self.t = 0
        self.next_id = 0
        self.agents: dict[int, Agent] = {}   # full ledger, dead included (lineage)
        self.live_ids: set[int] = set()      # index of living agents
        self.graph = nx.Graph()
        self.resources = cfg.resource_capacity
        self.events: list[dict] = []           # full event log
        self.window_events: list[dict] = []    # events since last observer tick
        self.global_memory: list[dict] = []    # all S(t)
        self.snapshots: list[dict] = []        # periodic network snapshots (for viz)
        self.broadcast_memory: list[dict | None] = []  # what agents were told, per tick
        self.current_broadcast: dict | None = None

        for _ in range(cfg.initial_population):
            self._add_agent(spawn_initial(self.rng, cfg, self._new_id(), 0))
        ids = sorted(self.agents)
        for aid in ids:
            for _ in range(cfg.initial_edges_per_agent):
                other = self.rng.choice(ids)
                if other != aid:
                    self.graph.add_edge(aid, other)

    # ---------------- main loop ----------------

    def run(self, steps: int | None = None) -> None:
        for _ in range(steps if steps is not None else self.cfg.steps):
            self.step()

    def step(self) -> None:
        cfg = self.cfg
        self.t += 1
        regen = (cfg.resource_base_regen
                 + cfg.resource_regen_rate * self.resources
                 * (1.0 - self.resources / cfg.resource_capacity))
        self.resources = min(cfg.resource_capacity, self.resources + regen)

        for aid in sorted(self.live_ids):
            self._act(self.agents[aid])

        self._process_deaths()

        if cfg.condition != "A" and self.t % cfg.observer_interval == 0:
            s_t = compute_self_model(self.t, self.graph, self.agents, self.window_events)
            self.global_memory.append(s_t)
            if cfg.condition == "R":
                idx = min(len(self.broadcast_memory),
                          len(cfg.replay_trajectory) - 1)
                self.current_broadcast = cfg.replay_trajectory[idx]
            else:
                self.current_broadcast = make_broadcast(
                    cfg.condition, s_t, self.signal_rng, cfg.distortion)
            self.broadcast_memory.append(self.current_broadcast)
            if self.current_broadcast is not None:
                for aid in sorted(self.live_ids):
                    self.agents[aid].received_global = self.current_broadcast
            self.window_events = []
        elif cfg.condition == "A" and self.t % cfg.observer_interval == 0:
            # Condition A still logs the macrostate for analysis (post-hoc only,
            # computed identically) so all conditions share one analysis pipeline.
            s_t = compute_self_model(self.t, self.graph, self.agents, self.window_events)
            self.global_memory.append(s_t)
            self.broadcast_memory.append(None)
            self.window_events = []

        if cfg.snapshot_interval > 0 and self.t % cfg.snapshot_interval == 0:
            self._take_snapshot()

        if cfg.shock_step > 0 and self.t == cfg.shock_step:
            self._apply_shock()

    # ---------------- agent behaviour ----------------

    def _act(self, agent: Agent) -> None:
        cfg = self.cfg
        agent.age += 1
        agent.energy -= cfg.metabolism

        w = self._action_weights(agent)
        action = self._weighted_choice(w)

        if action == "harvest":
            take = min(cfg.harvest_rate, self.resources)
            gained = take * (0.5 + 0.5 * agent.traits["risk"])
            self.resources -= take
            agent.energy += gained
            self._log("harvest", agent=agent.id, amount=round(gained, 3))
        elif action == "share":
            nbrs = sorted(n for n in self.graph.neighbors(agent.id)
                          if self.agents[n].alive)
            if nbrs and agent.energy > cfg.share_amount + 2.0:
                target = self.rng.choice(nbrs)
                agent.energy -= cfg.share_amount
                self.agents[target].energy += cfg.share_amount * 0.9  # costly helping
                self._log("share", agent=agent.id, target=target)
                agent.remember(("shared_with", target))
        elif action == "connect":
            candidates = sorted(a for a in self.agents
                                if self.agents[a].alive and a != agent.id
                                and not self.graph.has_edge(agent.id, a))
            if candidates:
                # Prefer neighbors-of-neighbors (local view), fall back to random.
                nn = sorted({m for n in self.graph.neighbors(agent.id)
                             for m in self.graph.neighbors(n)}
                            & set(candidates))
                pool = nn if (nn and self.rng.random() < 0.7) else candidates
                target = self.rng.choice(pool)
                agent.energy -= cfg.action_cost
                self.graph.add_edge(agent.id, target)
                self._log("connect", agent=agent.id, target=target)
        elif action == "prune":
            nbrs = sorted(self.graph.neighbors(agent.id))
            if nbrs:
                # Under high reported centralization, preferentially drop hub ties.
                bc = agent.received_global
                if bc and bc.get("centralization", 0) > 0.6 and self.rng.random() < \
                        agent.traits["global_sensitivity"]:
                    target = max(nbrs, key=lambda n: (self.graph.degree(n), n))
                else:
                    target = self.rng.choice(nbrs)
                self.graph.remove_edge(agent.id, target)
                self._log("prune", agent=agent.id, target=target)
        elif action == "reproduce":
            if (agent.energy >= cfg.reproduce_threshold
                    and agent.age >= cfg.min_reproduce_age
                    and len(self.live_ids) < cfg.max_population):
                agent.energy -= cfg.reproduce_cost
                child = spawn_child(self.rng, cfg, self._new_id(), agent, self.t)
                self._add_agent(child)
                self.graph.add_edge(agent.id, child.id)
                agent.offspring_count += 1
                self._log("birth", agent=child.id, parent=agent.id,
                          generation=child.generation)
        # "idle" does nothing

    def _action_weights(self, agent: Agent) -> dict:
        """Explicit, inspectable mapping: traits + local state + global signal → propensities."""
        tr = agent.traits
        cfg = self.cfg
        w = {
            "harvest": 1.0 + (1.0 if agent.energy < 15 else 0.0),
            "share": 0.6 * tr["cooperation"] * tr["sharing"],
            "connect": 0.4 * tr["sociability"] + 0.3 * tr["exploration"],
            "prune": 0.08,
            "reproduce": 0.5 if agent.energy >= cfg.reproduce_threshold else 0.0,
            "idle": 0.2,
        }
        bc = agent.received_global
        if bc is not None:
            base_repro = w["reproduce"]
            base_nonrepro = sum(v for k, v in w.items() if k != "reproduce")
            g = tr["global_sensitivity"] * cfg.feedback_gain
            if cfg.response_mode == "corrective":
                # Repair reported deficits (the default mechanism under test):
                w["connect"] += g * max(0.0, bc["fragmentation"] - 0.3)        # reconnect when told world is fragmenting
                w["share"] += g * max(0.0, 0.5 - bc["cooperation"])            # repair reported cooperation deficit
                w["share"] += g * 0.5 * max(0.0, bc["inequality"] - 0.5)       # redistribute when told inequality is high
                w["harvest"] += g * max(0.0, bc["turnover"] - 0.5)             # hoard when told times are unstable
                w["prune"] += g * 0.3 * max(0.0, bc["centralization"] - 0.6)   # decentralize when told hubs dominate
            else:
                # Conformist: imitate the reported norm rather than repair it.
                w["share"] += g * bc["cooperation"]                # share as much as "everyone" reportedly does
                w["prune"] += g * 0.5 * bc["fragmentation"]        # a fragmenting world licenses cutting ties
                w["connect"] += g * max(0.0, 0.6 - bc["fragmentation"])  # a cohesive world licenses linking
                w["harvest"] += g * bc["inequality"]               # an unequal world licenses accumulation
            if cfg.reproduction_neutral and base_repro > 0.0:
                # Feedback mass D_i went entirely to non-reproductive actions;
                # rescaling reproduce by (1 + D_i/N_0) makes P(reproduce) after
                # normalization identical to its no-broadcast value, so any
                # remaining selection on global_sensitivity is ecological rather
                # than a direct reproductive-opportunity cost.
                added = sum(v for k, v in w.items() if k != "reproduce") - base_nonrepro
                w["reproduce"] = base_repro * (1.0 + added / base_nonrepro)
        return w

    def _weighted_choice(self, weights: dict) -> str:
        items = sorted(weights.items())
        total = sum(v for _, v in items)
        r = self.rng.random() * total
        acc = 0.0
        for k, v in items:
            acc += v
            if r <= acc:
                return k
        return items[-1][0]

    # ---------------- lifecycle ----------------

    def _process_deaths(self) -> None:
        for aid in sorted(self.live_ids):
            a = self.agents[aid]
            cause = None
            if a.energy <= 0:
                cause = "starvation"
            elif a.age >= a.max_lifespan:
                cause = "old_age"
            if cause:
                a.death_time = self.t
                a.cause_of_death = cause
                self.live_ids.discard(aid)
                if self.graph.has_node(aid):
                    self.graph.remove_node(aid)
                self._log("death", agent=aid, cause=cause, age=a.age,
                          offspring=a.offspring_count)

    def _apply_shock(self) -> None:
        degs = sorted(self.graph.degree(), key=lambda kv: (-kv[1], kv[0]))
        if self.cfg.shock_fraction > 0:
            k = max(1, int(self.cfg.shock_fraction * len(self.live_ids)))
        else:
            k = self.cfg.shock_hubs_removed
        hubs = [n for n, _ in degs[:k]]
        for aid in hubs:
            a = self.agents[aid]
            if a.alive:
                a.death_time = self.t
                a.cause_of_death = "shock"
                self.live_ids.discard(aid)
                self.graph.remove_node(aid)
                self._log("death", agent=aid, cause="shock", age=a.age,
                          offspring=a.offspring_count)
        self._log("shock", removed=len(hubs))

    def _take_snapshot(self) -> None:
        """Record the live network for visualization. Consumes no randomness,
        so snapshots never affect determinism."""
        self.snapshots.append({
            "t": self.t,
            "nodes": [[aid, round(self.agents[aid].energy, 2),
                       self.agents[aid].generation]
                      for aid in sorted(self.live_ids)],
            "edges": sorted(tuple(sorted(e)) for e in self.graph.edges()),
        })

    # ---------------- bookkeeping ----------------

    def _new_id(self) -> int:
        self.next_id += 1
        return self.next_id - 1

    def _add_agent(self, agent: Agent) -> None:
        self.agents[agent.id] = agent
        self.live_ids.add(agent.id)
        self.graph.add_node(agent.id)

    def _log(self, etype: str, **kw) -> None:
        ev = {"t": self.t, "type": etype, **kw}
        self.events.append(ev)
        self.window_events.append(ev)

    def population(self) -> int:
        return len(self.live_ids)

    def state_hash(self) -> str:
        """Digest of the complete live state — used by the seed-replay check."""
        living = {
            aid: [a.generation, round(a.energy, 6), a.age,
                  [round(a.traits[k], 6) for k in sorted(a.traits)]]
            for aid, a in sorted(self.agents.items()) if a.alive
        }
        edges = sorted(tuple(sorted(e)) for e in self.graph.edges())
        blob = json.dumps([self.t, round(self.resources, 6), living, edges],
                          sort_keys=True)
        return hashlib.sha256(blob.encode()).hexdigest()

    # ---------------- persistence ----------------

    def save(self, outdir: str) -> None:
        os.makedirs(outdir, exist_ok=True)
        with open(os.path.join(outdir, "config.json"), "w") as f:
            f.write(json.dumps({"seed": self.seed,
                                **json.loads(self.cfg.to_json())}, indent=2))
        with open(os.path.join(outdir, "events.jsonl"), "w") as f:
            for ev in self.events:
                f.write(json.dumps(ev) + "\n")
        with open(os.path.join(outdir, "global_states.jsonl"), "w") as f:
            for s in self.global_memory:
                f.write(json.dumps(s) + "\n")
        with open(os.path.join(outdir, "nodes.jsonl"), "w") as f:
            for aid, a in sorted(self.agents.items()):
                f.write(json.dumps({
                    "id": aid, "generation": a.generation, "parent": a.parent_id,
                    "birth": a.birth_time, "death": a.death_time,
                    "cause": a.cause_of_death, "age": a.age,
                    "offspring": a.offspring_count,
                    "traits": {k: round(v, 4) for k, v in a.traits.items()},
                }) + "\n")
        with open(os.path.join(outdir, "edges_final.jsonl"), "w") as f:
            for u, v in sorted(tuple(sorted(e)) for e in self.graph.edges()):
                f.write(json.dumps({"source": u, "target": v}) + "\n")
        with open(os.path.join(outdir, "snapshots.jsonl"), "w") as f:
            for snap in self.snapshots:
                f.write(json.dumps(snap) + "\n")
        with open(os.path.join(outdir, "broadcasts.jsonl"), "w") as f:
            for b in self.broadcast_memory:
                f.write(json.dumps(b) + "\n")
