# Project ONE — Consolidated findings across all campaigns (Aug 2026)

**Evidence base: 927 core runs + 300 reproduction-neutral + 300 γ-free-pruning control runs = 1,527 total.** Core campaigns: (250 flagship + 150 harsh shock + 360 sweep + 90 conformist + 32 scale check + 30 replay-control receiving runs + 15 replay-source runs). Flagship (5 conditions × 50 paired seeds, mild shock),
harsh shock (5 × 30, 40% hub removal), sensitivity sweep (6 tokens × 20 seeds ×
3 feedback gains, harsh shock). Runs are 3000–4000 steps (the 2× scale
campaign uses 3000 steps with shock at t=1500; all others shock at t=2000),
deterministic, seed-replayable.
Statistics: PAIRED Wilcoxon signed-rank on per-seed differences (primary) with
matched-pairs rank-biserial r (tie-corrected via average ranks) and bootstrap
CIs; Mann-Whitney U / Cliff's δ retained as a SECONDARY robustness view — it does
not agree everywhere (e.g. harsh F-vs-A fragmentation: paired p=0.28,
unpaired p=0.013), and all inferential claims follow the paired analysis. Raw runs
regenerable via `scripts/campaign.py`.

**RNG note (Aug 2026 revision):** broadcast-signal generation now uses a
dedicated RNG stream (`signal_rng`), so constructing the noise signal never
advances the behavioral PRNG. (Once treatments alter agent actions, different
action branches naturally consume different subsequent behavioral draws —
that is the treatment effect, not a confound.) Non-noise conditions are
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
each p < 2e-5) and between-condition contrasts of ΔP are null in BOTH
campaigns (F vs N: harsh p=0.084, flagship p=0.63; R vs N p=0.95).
Conclusion: no evidence of content-specific attraction of the macrostate
toward broadcast content; raw P is dominated by intrinsic dynamics (post-shock
relaxation, drift toward typical states) that align best with realistic
references. The former "plausibility grades the steering channel" and "false
beats noise" steering findings are superseded by this analysis
(`scripts/passive_null_checks.py`, `campaigns/passive_null_checks.json`).
Supporting facts: F keeps 4/5 corrective rules active ≥90% of ticks while R is
mostly quiescent (mean |b−s|: 0.64 F / 0.36 N / 0.10 R) yet shows the largest
raw pull; excluding the shock transition shifts every median by <0.0004 absolute
(relative: −1.5% R, −2.6% F, −10% N) and changes no conclusion.

## Finding 3 — Attention declines under consequential broadcasts (dose-ordered)
Global-sensitivity (heritable attention to the broadcast) declines across
generations. Δ mean trait, end−start (harsh shock, g=0.8): no feedback −0.03
(neutral drift) · truth −0.10 (r=−0.59, p=0.004) · noise −0.34 (r=−0.94,
p≈2e-7) · lie −0.42 (r=−1.00, p≈2e-9). The sweep is dose-ordered: the
decline under the lie deepens from −0.12 (g=0.2) to −0.45 (g=1.6), and even
TRUE feedback shows a marked decline at high gain (−0.24 at g=1.6). None of
this ordering was programmed; it emerged from the evolutionary dynamics —
and unlike models where agents update trust from observed accuracy, here
attention is inherited and mutated with no rule referencing reliability:
trust is not updated, it evolves.

**Intensity relationship (`scripts/attention_cost.py`,
`campaigns/attention_cost.json`).** Veracity alone does not organize the
response — the utopia lie is false yet produces no decline, while truthful
feedback declines substantially at high gain. Defining the
*broadcast-implied corrective-drive intensity* I = g·⟨Σ_a f_a(b(t))⟩
(computable from the broadcast alone), evolved attention tracks I almost
perfectly across the 15 sweep cells: Spearman ρ = −0.99 (run level −0.83,
n=300; ρ = −0.99 with the zero-intensity utopia cells excluded, n=12). Utopia
(I=0) is untouched; truth declines less where its corrective drive is
smaller at equilibrium; unreliable high-drive broadcasts pay most.
CAVEAT: I deliberately omits the per-agent factor γ_i — the very quantity
under selection — and is computed from realized (already feedback-affected)
trajectories rather than independently randomized ones. This relationship is
therefore DESCRIPTIVE, not a causal mediation result; the paper states it
at that level.

**Reproduction-neutral control (`scripts/reproduction_neutral_check.py`,
`campaigns/reproduction_neutral_check.json`, campaigns/rn_g*).** Feedback adds
weight only to non-reproductive actions, so after normalization
P(reproduce | γ_i, b) = w_r / (W_0 + γ_i·g·D(b)) is DECREASING in γ_i whenever
the drive D(b) > 0 — and I is exactly the quantity governing that penalty, so
the correlation above could in principle be architectural rather than
ecological. Controlled by rescaling the reproduce weight by (1 + γ_i·g·D/N_0),
which holds the reproduce-ACTION SELECTION probability exactly at its
no-broadcast value, leaving all non-reproductive feedback weights unchanged
(verified: spread 0.00000 across γ ∈ [0,1], vs 0.209→0.134 uncontrolled).
Rerunning the full sweep (300 runs, config flag
`reproduction_neutral=True`): median retention 98% across all twelve cells
with a negative baseline Δγ̄ (99% across the ten with Δγ̄ < −0.05); at g=0.8 invert −0.410→−0.407, crisis −0.449→−0.439, noise −0.348→−0.305,
utopia +0.006 unchanged; no cell shows a significant paired shift; the
intensity correlation persists (ρ = −0.99 → −0.98). Truth in fact declines
MORE under the control (−0.087→−0.218 at g=0.8), the opposite of a dilution
artifact. Conclusion: selection on γ is ecological, not a direct
reproductive-opportunity cost. (With the flag off the engine reproduces all
stored campaign state hashes bit-for-bit.)

**γ-free pruning control (`PO_VARIANT=pgf scripts/reproduction_neutral_check.py`,
`campaigns/pruning_gamma_free_check.json`, campaigns/pgf_g*).** A second
architectural asymmetry: hub-targeted pruning fires with probability γ_i, NOT
γ_i·g — so receiver sensitivity has a second behavioral channel on a
different scale from every other feedback response, and one that acts
directly on network structure. Controlled by fixing that probability at 0.5
for every agent (config flag `pruning_gamma_free=True`), which removes γ's
influence on pruning-target selection while preserving the mechanism and
consuming the identical RNG draw. Rerunning the full sweep (300 runs): median
retention **100%** across all twelve cells with a negative baseline Δγ̄ (100%
across the ten with Δγ̄ < −0.05); at g=0.8 invert −0.410→−0.374,
crisis −0.449→−0.443, noise −0.348→−0.270, truth −0.087 unchanged,
utopia +0.006 unchanged; the intensity correlation STRENGTHENS
(ρ = −0.993 → −1.000, 15 cells). One of fifteen cells shows a significant
paired shift (N@g0.8, p = 0.033) — at α = 0.05 across 15 cells this is what
chance produces, and it is a partial ATTENUATION of a decline that still
retains 77% of its magnitude, not a reversal. The paper discloses this cell
explicitly rather than summarising the controls as "neither changes the
result"; the intensity ordering tightens under the control (ρ vs I:
−0.993 → −1.000), so the disclosed cell does not disturb it. Conclusion: the γ-in-pruning
asymmetry does not manufacture the evolutionary result either. Cells where
γ never enters pruning (C and F:utopia, whose broadcasts never report
centralization > 0.6) are bit-identical by construction, as expected.

**Mechanism note (`scripts/selection_mechanism.py`,
`campaigns/selection_mechanism.json`; 5 seeds, harsh shock, g=0.8, medians
over seeds).** The remaining individual-level pathway is not explained by
either simple candidate:

- NOT a negative marginal fecundity gradient. Within-run
  ρ(γ_i, lifetime offspring) over all agents reaching reproductive age is
  **+0.093 under F:invert** — the very condition where γ falls fastest —
  against −0.052 under A (no broadcast) and +0.014 under C. If anything,
  high-γ agents out-reproduce inside a run; the decline is not a fecundity
  penalty.
- NOT shock mortality. Shock victims' mean γ exceeds the mean of the
  population alive at the shock by only +0.027, and disabling the shock
  entirely leaves the decline intact (−0.404 no-shock vs −0.391 with).

Lineage depth: max generation reached is 21–22 and mean generation among
survivors ≈ 16–17, which is the basis for the paper's "~20 generations"
(NOT ~40 — an earlier draft conflated population replacements with lineage
depth). The pathway plausibly runs through lineage survival / energy budgets
downstream of reproduction; identifying it precisely is an open item
(reported as open in the paper).

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
In BOTH main campaigns, every paired Δmedian is exactly 0 and every p > 0.22:
flagship medians 10 steps (15 under F), harsh-shock medians 40 steps in every
condition even with 40% of hubs removed. Within the regimes tested, resilience
appears demographic (fast regrowth) rather than informational.

ONE CONTRARY LEAD, reported rather than buried: in the 2× scale campaign
F:invert vs A gives Δmedian +10 steps with all five non-tied pairs moving the
same way (tie-corrected r = +1.00, p = 0.0625). With n = 8 pairs, 0.0625 is
the SMALLEST p a two-sided Wilcoxon signed-rank can return, so this cannot
reach α = 0.05 by construction — it is neither significant nor dismissible.
It does not replicate at base scale (flagship F p = 0.32, harsh-shock F
p = 0.46). Treat as a lead for a larger-n scale campaign, not a result. The
paper states it in these terms rather than claiming the null holds "in any
condition or campaign" (an earlier draft did, and that was too strong).

## Paper-ready headline
Being measured changes nothing; being told changes much — but not by pulling
reality toward the story. Apparent self-fulfilling steering vanishes against
a passive counterfactual (Finding 2, a caution for empirical performativity
claims). What broadcasts really change is behavior and structure, with the
lie–response pair deciding which lies come true (Findings 4–6). Long run:
heritable attention declines across generations under consequential
broadcasts, tracking broadcast-implied corrective-drive intensity (Finding 3; individual-level pathway open, and
the intensity relationship descriptive). Together: self-model feedback is
a real causal channel whose credibility is itself an evolving property of
the system.

## Pre-specification disclosure (also stated as a labelled paragraph in the paper's Methods)
Four outcome FAMILIES were frozen in docs/PLAN.md before the first campaign
(recovery, fragmentation, cooperation, self-model correspondence). The
story-pull statistic is a later directional refinement of the correspondence
outcome (the original distance-based metric is degenerate under truthful
feedback); both give the same raw F-vs-N ordering, and the passive-null
analysis above governs its causal interpretation. The replay (R) and
passive-counterfactual analyses were added during review.
