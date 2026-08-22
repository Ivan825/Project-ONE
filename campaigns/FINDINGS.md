# Project ONE — Consolidated findings across all campaigns (Aug 2026)

**Evidence base (as reported in the manuscript): 927 core + 300 reproduction-neutral + 300 γ-free-pruning + 400 evolvable-polarity control runs + 1,200 ecology-ensemble runs = 3,127 total.** A further follow-up study (64-cell response policies, gain and rule-form sweeps, selection-timing checks) is documented separately in `docs/PAPER2_PLAN.md` and is NOT part of the manuscript's evidence base. Core campaigns: (250 flagship + 150 harsh shock + 360 sweep + 90 conformist + 32 scale check + 30 replay-control receiving runs + 15 replay-source runs). Flagship (5 conditions × 50 paired seeds, mild shock),
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

**Threshold and cadence sensitivity (`scripts/eps_sensitivity_deltap.py`,
`scripts/dt_sensitivity_deltap.py`).** Two measurement choices could in
principle drive the passive-counterfactual result. (a) The movement threshold:
recomputing ΔP under ε ∈ {0.01, 0.02, 0.05} leaves every gap negative (all
p < 2e-5) and the adjusted F-vs-N contrast non-significant at every threshold
(p = 0.088 / 0.084 / 0.052) — the conclusion does not depend on ε. (b) The
observer interval Δt is NOT a comparable robustness axis: retiming the
observer retimes the feedback dose itself, so Δt ∈ {5, 10, 20} is a sweep over
treatments, not measurements. Run anyway (270 runs, A/F/N × 30 paired seeds
per cadence), and reported in full because the naive "stability" framing would
be false:

| Δt | raw P (F) | passive (F) | ΔP (F) | raw P (N) | passive (N) | ΔP (N) |
|---|---|---|---|---|---|---|
| 5 | 0.0007 | 0.0005 | +0.0001 | −0.0016 | 0.0031 | −0.0049 |
| 10 (paper) | 0.0078 | 0.0119 | −0.0036 | 0.0014 | 0.0073 | −0.0055 |
| 20 | 0.0091 | 0.0074 | +0.0010 (ns) | 0.0125 | 0.0087 | +0.0036 (p=.017) |

The paper's conclusion — raw P is dominated by intrinsic passive dynamics —
replicates at every cadence: the passive twin is the same order as raw P
throughout (~75–80% of it at Δt=20), and at Δt=5 the raw pull nearly vanishes
altogether. What varies is the small residual, |ΔP| ≤ 0.005, which flips sign
with cadence (slightly positive at slow re-dosing, N at Δt=20: +0.0036,
uncorrected p=0.017). Exploratory, uncorrected, and outside the paper's
pre-registered design; the manuscript therefore treats Δt as a treatment
parameter and points here rather than claiming stability it does not have.

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
(ρ = −0.993 → −1.000, 15 cells). One of fifteen cells shows an uncorrected significant
paired shift (N@g0.8, p = 0.033) — at α = 0.05 across 15 cells this is what
chance produces, and it is a partial ATTENUATION of a decline that still
retains 77% of its magnitude, not a reversal. It is also one of the nine
contrasts demoted in the m = 74 multiplicity family below, so the paper
calls it an *uncorrected* shift rather than a significant one. The paper discloses this cell
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
loop implements distributed corrective feedback. **False and noise broadcasts**
densify and flatten the network (mean degree +3.8 lie / +2.8 noise; Freeman
centralization and betweenness concentration fall under both). The truth arm
(+1.1, r=0.49) is reported as a within-campaign figure only: it is significant
in just 1 of 24 ecologies and correct-signed in 16, so the general claim is
scoped to the distortions — see the ecological-robustness section below.

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

**Evolvable response strength/polarity control (`scripts/policy_campaign.py`,
`campaigns/policy_campaign/`).** The three controls above all hold the response
mapping f_a FIXED, so a critic can still say that lowering γ is the only route
the architecture leaves open for disengaging from a broadcast. Controlled by
making the polarity and strength ρ_a ∈ [−2,2] of each action-channel response
heritable and mutated at reproduction (config `policy_mode="polarity"`):
ρ_a = 1 reproduces the hand-written rule BIT-IDENTICALLY (verified by test for
both the corrective and the conformist rule form), ρ_a = 0 ignores that
channel, ρ_a < 0 reverses it. The γ̄ decline persists with this second route
open — vs A at n=100: C −0.125 (p=2.0e-6), F −0.222 (p=6.8e-9), N −0.212
(p=2.5e-10). On matched seeds, freeing ρ ATTENUATES the decline under false
(+0.126, r=0.66) and noise (+0.165, r=0.65) feedback, both p≈0.001, but not
under truth (p=0.90): populations use both routes, and only where
disengagement pays. NOTE this is evolvable strength/polarity of a mechanistic
response basis — NOT a learned arbitrary policy; the underlying f_a still
exists. Only these three Δγ̄ contrasts enter the manuscript's inferential
family (m=77); the per-channel ρ analyses belong to the follow-up study.

**Rule-form control (`scripts/rule_form_check.py`,
`campaigns/rule_form_check.json`).** The two architectural controls hold the
response ARCHITECTURE fixed and remove a channel. This one holds the
architecture fixed and swaps the entire response function for a second,
structurally unrelated mapping designed independently for another purpose —
the conformist regime (raw levels, not deficit-gated). Two answers, pointing
opposite ways, and BOTH are reported in the paper:

1. The decline SURVIVES the rule swap. Under conformist rules γ̄ still falls
   in every broadcast condition relative to A on the shared seed list:
   C −0.559 (r=−1.00), F:utopia −0.568 (r=−1.00), N −0.535 (r=−1.00),
   F:invert −0.482 (r=−0.98), F:crisis −0.138 (r=−0.67); worst p = 0.022.
   So the PHENOMENON is not an artifact of the corrective rule form — the
   single most-repeated criticism of this work.
2. The intensity predictor does NOT transfer. Recomputing I with the
   conformist f_a gives ρ(I, Δγ̄) = +0.10, p = 0.87 over the 5 cells — a null,
   and the wrong sign. The ORDERING, and the I that summarises it, are
   rule-specific.

This is exactly what the paper's scope sentence claims ("a within-regime
ordering, not a quantity normalized for comparison across regimes"), so (2) is
a confirmation of that caveat rather than a surprise. Reporting (1) without
(2) would overstate the result; the script prints both and the paper states
both.

## Ecological robustness — do the headline claims depend on the baseline ecology?
(`scripts/ecology_ensemble.py`, `campaigns/ecology_ensemble/`)

Every review of this work raises "a single ecology and one parameter family".
The answer here is a randomized ensemble rather than a parameter sweep, run in
three stages with the anti-cherry-picking discipline built into the ordering.

**Design.** 24 candidate ecologies, each an independent uniform draw of ±25%
on six ecological parameters (`resource_base_regen`, `resource_capacity`,
`reproduce_cost`, `metabolism`, `action_cost`, `max_lifespan_mean`) from a
fixed `RandomState(20260820)`. Stage 1 ran ONLY the no-broadcast baseline
(condition A, 3 seeds each, 72 runs) and applied four viability criteria
**already frozen in the script before any broadcast condition was run**:
final population ≥ 20, ≤ 80% of the population cap, mean degree ≥ 2 at the
shock, and ≥ 8 generations of lineage depth. Stage 2 ran A/B/C/F/N × 10 paired
seeds on the frozen set (1,200 runs, harsh-shock protocol: 4,000 steps, 40%
hub removal at t=2000, gain 0.8). Because Stage 1 cannot see any treatment
outcome, no ecology could be admitted or dropped on the basis of whether it
produced the result we wanted.

**The screen did not bind.** All 24 candidates passed, and not narrowly — the
worst final population was 40 against a floor of 20, the worst mean degree
2.48 against 2.0, the worst lineage depth 15 generations against 8, and no
ecology exceeded 7.3% of the population cap. This is reported as what it is: a
pre-registered commitment that happened not to filter anything, which is a
stronger position against cherry-picking than a screen that rejected some
(there was no selection at all), but which also means the criteria were never
stress-tested.

**Metric fidelity.** The ensemble's outcome definitions are lifted from
`scripts/analyze_campaign.py`, and this is verified rather than asserted: at
UNPERTURBED parameters the ensemble reproduces `campaigns/harsh_shock/`
run-for-run — 16/16 outcomes to 1e-10 across A and C, seeds 1–2
(`--validate`). The same check doubles as proof that the v2 evolved-policy
machinery left the published code path untouched.

**Results — per-ecology paired Wilcoxon (n=10 seeds), counted across the 24.**

| claim | outcome | cond | significant | correct sign | median effect |
|---|---|---|---|---|---|
| cooperation up under truth | `cooperation_rate` | C | **24/24** | 24/24 | +0.184 |
| attention falls under the lie | `trait_gs_delta` | F | **24/24** | 24/24 | −0.396 |
| attention falls under noise | `trait_gs_delta` | N | **24/24** | 24/24 | −0.258 |
| attention falls under truth | `trait_gs_delta` | C | 13/24 | 22/24 | −0.169 |
| densifies under the lie | `mean_degree` | F | 18/24 | **24/24** | +5.82 |
| densifies under noise | `mean_degree` | N | 10/24 | **24/24** | +3.30 |
| densifies under truth | `mean_degree` | C | **1/24** | 16/24 | +0.60 |
| betweenness flattens | `betweenness_concentration` | F | 17/24 | **24/24** | −0.012 |
| betweenness flattens | `betweenness_concentration` | N | 8/24 | 22/24 | −0.008 |
| hubs flatten | `freeman_centralization` | F | 9/24 | 23/24 | −0.025 |
| hubs flatten | `freeman_centralization` | N | 7/24 | 22/24 | −0.017 |
| recovery unaffected | `recovery_time_90` | C/F/N | 22/24, 24/24, 24/24 | 24/24 | 0 |
| measurement inert | all outcomes | B | **24/24** | — | every per-seed difference exactly 0 |

The inertness row is stronger than the outcome-level statement suggests. Every
one of the **240** paired (ecology, seed) A-and-B runs has an identical SHA-256
state hash — bit-identical complete final state, not merely equal summary
outcomes — while A shares a hash with C, F and N in **0/240** cases. Running
the observer changes nothing; only broadcasting does.

Ordering **F ≤ N ≤ C ≤ A** in evolved attention holds exactly in **21/24**
ecologies; median rank correlation **+1.00**.

**What this establishes.** The three central results — the cooperation
doubling, the attention decline under consequential broadcasts, and the
observed-but-blind identity — replicate in every ecology tested, as does the
pre-specified recovery null. The dose-ordering, the most distinctive claim,
holds exactly in 21 of 24.

**What it does not.** *Densification under truthful feedback does not survive.*
Significant in 1 of 24 and correct-signed in only 16, against 24/24 on sign
for both distortions. This is the weakest of the three numbers in Sect. 5.2 to
begin with (+1.1, r=0.49 under C, against +3.8, r=0.80 under F and +2.8,
r=0.72 under N), and the ensemble reproduces the two distortion arms closely
(+5.8, +3.3) while the truth arm goes null. The claim should read *false and
noise broadcasts densify the network*, not *broadcasts densify the network*.

A confirmation in the same table: under C, Freeman centralization and
betweenness concentration come out 12/24 and 11/24 on sign — a coin flip.
That is precisely what the paper's rescoped flattening sentence predicts,
truth having been removed from that claim after direct checking.

**Limitation, stated rather than implied.** ±25% on six parameters produces
recognizably different worlds — per-ecology spreads of 2.5× in mean degree at
the shock (1.7× sustained), 2.2× in cooperation, 1.9× in population — but not
qualitatively different regimes. This is evidence of *local* ecological
robustness. It is not evidence that the results hold in an arbitrary ecology,
and the paper should not be read as claiming so.

**Cross-platform verification (incidental).** The 1,200 runs were split across
two machines and 31 runs were computed on both. Every state hash agreed, across
x86_64/Python 3.11.15/networkx 3.6.1 and aarch64/Python 3.10.12/networkx 3.4.2
— different CPU architecture, Python minor, and networkx minor, bit-identical
output. `--merge` performs this check automatically and refuses to merge on any
disagreement.

## Multiplicity (`scripts/multiplicity_check.py`, `campaigns/multiplicity_check.json`)
The confirmatory family is the eight numerical contrasts of the paper's
Table 3 (the other two rows carry no p-value: B-vs-A is an exact identity,
and the recovery row reports a bound). p-values are RECOMPUTED from the run
records by the script, not copied from the paper, so the check cannot inherit
a transcription error.

Uncorrected: 6 of 8 significant at α = 0.05.
Benjamini-Hochberg (FDR):   6 of 8 — every decision unchanged.
Holm-Bonferroni (FWER):     6 of 8 — every decision unchanged.

The margin is wide, not marginal: the largest surviving p is 9.5e-4 against a
Holm threshold of 0.05/3 = 0.0167 at that rank (~17x). The two contrasts that
fail are the two adjusted story-pull contrasts (p = 0.084 harsh, 0.63
flagship) — already reported as null, so correction cannot change the paper's
conclusions in either direction. Exploratory analyses (everything outside the
four pre-specified families) are interpreted through effect size, replication
and their labelled exploratory status rather than adjusted significance.

**Enlarged (hostile) family, m = 74.** Scoping a correction to the table that
needs it invites the objection that the family was picked to flatter the
result, so the script also applies both corrections to a superset: every
paired contrast reported anywhere in the paper. The family reached its final
size only on the third pass — 58, then 63 when the conformist rule-form check
was added, then 74 when an audit found the ten structural-spillover contrasts
of Sect. 5.2/5.3 were still missing (they are computed from raw trajectories
rather than results.json, which is why two earlier passes missed them). The
script now derives all of them, so it cannot go stale silently again.

At m = 74 the result is SPLIT, and the paper says so:

- **Benjamini-Hochberg (FDR): all eight Table 3 decisions unchanged.** This is
  the appropriate correction for a family of this size.
- **Holm-Bonferroni (FWER): one demotion.** Fragmentation (FL) F vs A, the
  weakest of the eight at p = 9.5e-4, sits just under the Holm threshold
  (rank 13/74 → 0.05/62 = 8.06e-4). It survived at m = 58 and m = 63; the
  family growing past ~70 is what demotes it.

Reporting only the m = 8 or m = 63 result would have been the convenient
choice. The honest statement is that the confirmatory decisions are robust to
FDR control over every test in the paper, and all but the weakest are robust
to FWER control as well.

Nine contrasts OUTSIDE Table 3 are demoted at m = 74, none load-bearing: the
four 2x scale-check contrasts (stated as n = 8), the gamma-free-pruning
N@g0.8 cell, the conformist F:crisis rule-form contrast, and three
structural-spillover contrasts (mean degree HS C vs A, Freeman HS N vs A,
betweenness HS N vs A) that the paper reports as effect sizes rather than as
significance claims.

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
