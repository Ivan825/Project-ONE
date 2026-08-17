# Project ONE

**What happens to a population of agents when it is told its own collective state — and what happens when that description is false?**

Project ONE is a controlled laboratory for *recursive self-model feedback* in evolving multi-agent networks. Temporary, locally-limited agents are born, interact, cooperate, compete, reproduce and die, collectively forming a changing network G(t). A global observer periodically compresses the network's macrostate into a self-model S(t) — population, fragmentation, centralization, cooperation, inequality — and, in the key experimental conditions, broadcasts that self-model back into the world it describes.

The system therefore closes a loop that most real systems (markets, organizations, online platforms, and now LLM-agent collectives) already live inside:

```
local actions → global condition → measurement → self-model → broadcast → changed local actions
```

The flagship experiment asks whether a distributed system can be causally altered by a *wrong* representation of itself — self-fulfilling collapse, self-defeating panic, manufactured coordination.

## Experimental conditions

| Condition | Observer measures | Agents receive |
|---|---|---|
| **A** — Local Only | no | nothing |
| **B** — Observed but Blind | yes | nothing |
| **C** — True Feedback | yes | accurate S(t) |
| **F** — False Feedback | yes | systematically distorted S(t) |
| **N** — Noise Feedback | yes | matched-bandwidth random signal |

Condition N separates "any broadcast changes behaviour" from "*self*-information changes behaviour." Condition B separates the act of measurement from the act of feedback. All conditions run from matched parameter distributions with paired random seeds; comparisons are between outcome distributions, never single runs.

## Pre-registered primary outcomes

1. **Recovery half-life** after a standardized shock (targeted hub removal)
2. **Fragmentation trajectory** (weakly connected community structure over time)
3. **Cooperation rate** (costly-helping interactions per capita)
4. **Self-model correspondence** — in Condition F: does reality converge toward the false description (self-fulfilling) or away from it (self-defeating)?

All other logged measurements (entropy, diversity, inequality, legacy, novelty, continuity…) are secondary and exploratory by design.

## Quickstart

```bash
pip install -r requirements.txt
python run.py --condition C --steps 2000 --seed 42
python run.py --condition F --steps 2000 --seed 42 --distortion invert
python scripts/replay_check.py                     # exact seed-replay determinism
python scripts/validate_metrics.py                 # observer metrics vs. known cases
python scripts/dashboard.py runs/C_s42_n2000       # self-contained HTML dashboard
```

The dashboard is a single HTML file: macrostate timelines (with shock markers), an animated force-layout network with a time scrubber, and a click-to-inspect agent panel showing traits, lineage and cause of death. Open it in any browser — no server needed.

Every run is fully reproducible from its config and seed. Runs write four datasets — nodes, edges, events, global states — sufficient to reconstruct the entire history.

## Design principles

- **Rule-based agents first.** Transparent trait vectors (cooperation, exploration, risk, sociability, sharing, global-sensitivity), not learned policies — so every behavioural change is inspectable. LLM agents are a later, separate experimental phase.
- **Falsifiable by construction.** Null results are results. If self-information adds nothing beyond matched noise, that finding is published as such.
- **Ablations over anecdotes.** No single visually-striking run is evidence; distributions across ≥50 seeds per condition are.

## Roadmap

M0 deterministic engine → M1 stable ecology → M2 observer + metric validation → M3 flagship runs (A/B/C/F/N) → M4 preprint + this repo goes public → ALIFE submission → Paper 2 (continuity under total turnover) → Phase L (LLM agents).

See [`docs/PLAN.md`](docs/PLAN.md) for the full research plan and [`docs/`](docs/) for the original proposal.

## Status

Early development (M0). Contributions, criticism and replication attempts are welcome — open an issue.

## License

MIT
