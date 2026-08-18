# Project ONE

**What happens to a population of agents when it is told its own collective state — and what happens when that description is false?**

![Sensitivity sweep](campaigns/sweep_summary.png)

Project ONE is a controlled, fully reproducible laboratory for *recursive self-model feedback* in evolving multi-agent networks. Temporary agents are born, cooperate, compete, reproduce and die, forming an adaptive network G(t). A global observer periodically compresses the macrostate — fragmentation, cooperation, centralization, inequality, turnover — into a self-model S(t) and, depending on the experimental condition, broadcasts it back to the agents **accurately, systematically falsified, or as matched-bandwidth noise**:

```
local actions → global condition → measurement → self-model → broadcast → changed local actions
```

## Headline findings (927 runs, pre-specified outcomes)

**Measurement alone is causally inert.** The observed-but-blind condition is trajectory-identical to no-observer under paired seeds — Cliff's δ = 0.000 on every outcome, twice replicated. Only the *broadcast* has causal power.

**A false self-model pulls reality toward itself (under corrective responses).** Macrostate movement toward the broadcast ("story pull") exceeds the matched-noise control at every feedback gain tested (paired rank-biserial r = 0.84–0.88, p ≈ 10⁻⁶–10⁻⁸, robust to the ε threshold), and a replayed *genuine* self-model from another run — a realistically structured false description — steers hardest of all: steering power is graded by the realism of the description's structure, not by how often response rules fire. A quiet, systematic lie out-steers loud noise ~7× at low gain.

**Which lies come true depends on how agents respond.** Under corrective agents, an alarmist lie is self-defeating and a flattering lie is behaviorally inert. Under conformist agents the taxonomy flips: the alarmist lie becomes catastrophically self-fulfilling (fragmentation ×10) and the flattering lie becomes benevolently self-fulfilling (highest cooperation observed).

**Populations fed lies evolve to stop listening.** Attention to the broadcast is a heritable trait; its population mean declines across generations, more strongly with increasing broadcast unreliability and volume — false (δ = −0.94) > noise > truth > silence — with a clean dose-response in feedback gain. Nobody programmed that ordering, and the pathway is not a simple fecundity gradient (see FINDINGS).

![Evolution of distrust](campaigns/harsh_shock/fig8_trait_evolution.png)

**Truthful feedback doubles costly cooperation** (δ = 0.96, monotone in gain) — the loop implements distributed corrective feedback. And one pre-specified null, twice replicated: we detected no evidence of a feedback effect on post-shock recovery time, even at 40% hub removal.

Full statistics: [`campaigns/FINDINGS.md`](campaigns/FINDINGS.md) · interactive explorer: `campaigns/flagship/report.html`

## Reproduce everything

```bash
pip install -r requirements.txt
python scripts/replay_check.py                   # exact seed-replay determinism (cross-platform)
python scripts/validate_metrics.py               # observer metrics vs. known closed-form cases
python run.py --condition F --distortion invert --steps 2000 --seed 7
python scripts/dashboard.py runs/F_s7_n2000      # self-contained interactive dashboard
python scripts/campaign.py --seeds 50 --shock-fraction 0.4 --out campaigns/replication
python scripts/analyze_campaign.py campaigns/replication
python scripts/demo.py                           # one-command live-demo kit
```

Every run is deterministic given (config, seed); state hashes verify replay across machines and operating systems. 13-test suite guards determinism, metric correctness, and population viability.

## Experimental design

| Condition | Observer | Agents receive |
|---|---|---|
| A — Local only | off | nothing |
| B — Observed, blind | on | nothing (placebo) |
| C — True feedback | on | accurate S(t) |
| F — False feedback | on | distorted S(t): invert / crisis / utopia |
| N — Noise feedback | on | matched-bandwidth random signal |
| R — Replayed self-model | on | genuine S(t) trajectory of another run |

Paired seeds across conditions; standardized hub-removal shocks; four pre-specified outcomes; paired Wilcoxon signed-rank primary analysis (Mann–Whitney U + Cliff's δ as robustness); robustness across feedback gains (0.2–1.6), two shock severities, 2× system scale, and two response regimes (corrective / conformist).

## Paper

*Steering a Network with Its Own Reflection: True, False, and Noise Self-Model Broadcasts in an Evolving Multi-Agent Network* — under submission to Complex Networks 2026. Draft and sources in [`paper/`](paper/). Research plan and the original proposal in [`docs/`](docs/).

## Status

Active research. Criticism, replication attempts, and issues welcome.

## License

MIT
