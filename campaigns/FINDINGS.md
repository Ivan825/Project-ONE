# Project ONE — Consolidated findings across all campaigns (Aug 2026)

**Evidence base: 927 runs** (250 flagship + 150 harsh shock + 360 sweep + 90 conformist + 32 scale check + 30 replay-control receiving runs + 15 replay-source runs). Flagship (5 conditions × 50 paired seeds, mild shock),
harsh shock (5 × 30, 40% hub removal), sensitivity sweep (6 tokens × 20 seeds ×
3 feedback gains, harsh shock). Runs are 3000–4000 steps (the 2× scale
campaign uses 3000 steps with shock at t=1500; all others shock at t=2000),
deterministic, seed-replayable.
Statistics: PAIRED Wilcoxon signed-rank on per-seed differences (primary) with
matched-pairs rank-biserial r (tie-corrected via average ranks) and bootstrap
CIs; Mann-Whitney U / Cliff's δ retained as robustness checks. Raw runs
regenerable via `scripts/campaign.py`.

**RNG note (Aug 2026 revision):** broadcast-signal generation now uses a
dedicated RNG stream (`signal_rng`), so conditions differ only in signal
CONTENT and never in behavioral-RNG consumption. Non-noise conditions are
bit-identical to the single-stream implementation (verified by state hash);
all N cells were regenerated under the two-stream scheme.

## Finding 1 — Measurement alone is causally inert (twice replicated)
Condition B (observed but blind) is trajectory-identical to A under paired
seeds: every per-seed difference exactly zero, on every outcome, in both the
flagship and harsh-shock campaigns. Only the *broadcast* has causal power.
(The engine computes S(t) in A as well, for analysis only, so this doubles as
a strict observer-side-effect invariance check.)

## Finding 2 — Apparent "story pull" is fully explained by a passive counterfactual
The raw story-pull statistic P (movement toward the reference where it differs
from the state) is positive and internally consistent in every signal
condition (harsh-shock medians: replay R 0.024 > inverted lie F 0.008 > noise
N 0.001; F vs N paired r=0.89, p≈2e-6; R robust to one-receiver-per-source and
source-clustered bootstrap). BUT scoring untreated paired-seed trajectories
(A/B) against the same reference types post hoc yields LARGER values: passive
medians 0.012 (invert), 0.030 (replay), 0.007 (noise). Per-condition causal
effects ΔP = P_actual − P_passive are uniformly negative (−0.004 to −0.006,
each p ≤ 1e-5) and between-condition contrasts of ΔP are null in BOTH
campaigns (F vs N: harsh p=0.084, flagship p=0.63; R vs N p=0.95).
Conclusion: no evidence of content-specific attraction of the macrostate
toward broadcast content; raw P is dominated by intrinsic dynamics (post-shock
relaxation, drift toward typical states) that align best with realistic
references. The former "plausibility grades the steering channel" and "false
beats noise" steering findings are superseded by this analysis
(`scripts/passive_null_checks.py`, `campaigns/passive_null_checks.json`).
Supporting facts: F keeps 4/5 corrective rules active ≥90% of ticks while R is
mostly quiescent (mean |b−s|: 0.64 F / 0.36 N / 0.10 R) yet shows the largest
raw pull; excluding the shock transition changes medians <2%.

## Finding 3 — Populations fed lies evolve to stop listening (dose-response)
Global-sensitivity (heritable attention to the broadcast) declines across
generations, more strongly the more misleading and the louder the broadcast
is. Δ mean trait, end−start (harsh shock, g=0.8): no feedback −0.03 (neutral
drift) · truth −0.10 (r=−0.59, p=0.004) · noise −0.34 (r=−0.94, p≈2e-7) ·
lie −0.42 (r=−1.00, p≈2e-9). The sweep shows a clean dose-response: the
decline under the lie deepens from −0.12 (g=0.2) to −0.45 (g=1.6), and even
TRUE feedback shows a marked decline at high gain (−0.24 at g=1.6). None of
this ordering was programmed; it emerged from the evolutionary dynamics.
Mechanism note: the individual-level pathway is NOT a simple fecundity
gradient — within-run ρ(γ_i, offspring count) ≈ +0.05 under F, the decline
persists without the shock (−0.40 no-shock vs −0.39 with), and shock victims'
mean γ is only +0.03 above the population mean. The pathway plausibly runs
through lineage survival / energy budgets downstream of reproduction;
identifying it precisely is an open item (reported honestly in the paper).

## Finding 4 — Not all lies are equal (outcome space, corrective regime)
- **Inverted lie**: keeps 4/5 corrective rules persistently active; mobilizes
  costly helping (+0.106 over baseline, flagship r=0.82) and drives
  over-connection (mean degree +3.8 vs A, r=0.80).
- **Crisis lie** (permanent alarm): self-defeating for structure — corrections
  push fragmentation AWAY from the alarmist story — while its constant
  cooperation-deficit signal drives the highest cooperation under correction
  (0.35–0.45 across gains).
- **Utopia lie** (everything is fine): behaviorally inert — identical to
  no-feedback on every outcome at every gain, because purely corrective
  response rules fire only on reported deficits. Breeds no distrust either,
  because attending to it is consequence-free.

## Finding 5 — The response regime decides which lies come true (outcomes)
Conformist agents reverse the taxonomy: the crisis lie becomes catastrophically
self-fulfilling (fragmentation 0.400 vs 0.038 baseline), the utopia lie
benevolently so (cooperation 0.428), and even noise mobilizes (cooperation
0.445 — imitation amplifies whatever is reported). Which lies come true, in
the outcome sense, is a property of the lie–response pair.

## Finding 6 — Truthful feedback doubles costly cooperation
0.397 vs 0.179 baseline (flagship paired Δmedian +0.200 [0.172, 0.239],
r=1.00, p≈9e-15; replicated harsh r=0.99), monotone in gain (0.27→0.48). The
loop implements distributed corrective feedback. Broadcasts also densify and
flatten the network (mean degree +1.1 truth / +3.8 lie / +2.8 noise; Freeman
centralization and betweenness concentration fall under lie and noise).

## Finding 7 — Pre-specified null: no detected feedback effect on recovery time
Even removing 40% of hubs, median population recovery is ~40 steps in every
condition (all p > 0.12): we detected no evidence of a feedback effect on
recovery time. Within the regimes tested, resilience appears demographic
(fast regrowth) rather than informational. Reported as observed.

## Paper-ready headline
Being measured changes nothing; being told changes much — but not by pulling
reality toward the story. Apparent self-fulfilling steering vanishes against
a passive counterfactual (Finding 2, a caution for empirical performativity
claims). What broadcasts really change is behavior and structure, with the
lie–response pair deciding which lies come true (Findings 4–6). Long run:
heritable attention to unreliable self-models declines across generations
(Finding 3; individual-level pathway open). Together: self-model feedback is
a real causal channel whose credibility is itself an evolving property of
the system.

## Pre-specification disclosure
Four outcome FAMILIES were frozen in docs/PLAN.md before the first campaign
(recovery, fragmentation, cooperation, self-model correspondence). The
story-pull statistic is a later directional refinement of the correspondence
outcome (the original distance-based metric is degenerate under truthful
feedback); both give the same raw F-vs-N ordering, and the passive-null
analysis above governs its causal interpretation. The replay (R) and
passive-counterfactual analyses were added during review.
