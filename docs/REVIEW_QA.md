# Rebuttal preparation — Stanford AI review of cn2026-submission

> Internal document. The review recommends acceptance; the paper is frozen and
> none of this goes into the manuscript. This triages the reviewer's ten
> questions into what is already answered by data in this repository, what is
> cheap analysis of stored runs, and what belongs to the follow-up study — so
> that a rebuttal or camera-ready response can be written from evidence rather
> than promises.

## Reading of the review

Every listed weakness is a limitation the manuscript itself states: stylized
rules ("mechanism probes, not calibrated models of behavior"), descriptive
rather than causal I (the caveats paragraph), cadence deferred to the
repository (deliberate — retiming the observer retimes the dose), lineage
decomposition left to future work (stated in Sect. 5.5). No number is
disputed and no control is claimed missing. The one genuinely new
methodological suggestion is Q6's dose-held-constant cadence design, which is
adopted into the Paper 2 plan below.

## The ten questions, triaged

**Q1 — ΔP under the conformist regime.**
*ANSWERED — computed from stored runs* (`scripts/review_response_checks.py`
→ `campaigns/review_response_checks.json`, same imported Eq.-2 code path as
the paper's passive checks; 15 paired seeds, harsh shock). The registered
prior was that the passive twin would absorb most of the raw pull; the result
is sharper than the prior: the twin absorbs roughly half (raw P_F 0.028 vs
passive 0.013), and a **positive** steering residual survives —
ΔP_F = +0.020 (Wilcoxon p = 6.1e-5, rank-biserial 1.0: every seed) and
ΔP_N = +0.023 (p = 6.1e-5, every seed), with the F-vs-N difference ns
(p = 0.52), i.e. content-independent, as in the corrective regime. This is
the mirror image of the corrective regime's negative ΔP and the strongest
possible answer to the question: the sign of the performativity gap is set by
the response rule, and the statistic detects genuine steering when steering
is there — which is what makes the corrective regime's away-from-story
correction informative rather than an artifact of the measure.

**Q2 — decompose structural effects by action channel.**
*Partially answered by data in hand; full ablation is Paper 2.* Two existing
results bear directly: (a) the γ-free-pruning control fixes the hub-pruning
probability for every agent and leaves the structural pattern intact —
so hub-targeted pruning's γ-coupling is not what drives the flattening;
(b) the evolvable-polarity campaign gives a per-channel decomposition of the
evolutionary response (ρ̄ vs A at n=100):

| cond | connect | harvest | prune | share |
|---|---|---|---|---|
| C | 0.945 | 1.052 | 1.103 | 0.746 |
| F | 0.341 | 1.038 | 0.913 | 0.534 |
| N | 0.770 | 1.094 | 0.942 | 0.567 |

Costly channels (share, connect) are suppressed under misleading feedback;
free (prune) and energy-yielding (harvest) channels are not. A third stored
result, the per-*statistic* decomposition in `passive_null_checks.json`
(`per_component`), shows actual-F pull sitting below its passive twin on
every broadcast component individually (largest gaps: turnover 0.033 vs
0.053, cooperation 0.0053 vs 0.0079) — the negative ΔP is not carried by a
single channel of the broadcast. A clean channel-masking ablation of the
*structural* outcomes is a Paper 2 experiment (its H-list already contains
the component question).

**Q3 — lineage-level decomposition of Δγ.**
*ANSWERED with stored evidence* (`review_response_checks.json`). The per-run
Robertson/Price selection differential S(γ) = cov(γᵢ, nᵢ)/n̄ over completed
lifetimes — the "differential reproduction" component the reviewer asks
about — comes from the 150 fixed-mode runs; sign structure by condition:

| cond | median S(γ) | frac < 0 | Wilcoxon p vs 0 | realized Δγ (median) |
|---|---|---|---|---|
| A | −0.0011 | 0.60 | 0.16 | −0.029 |
| C | −0.0003 | 0.53 | 0.63 | −0.103 |
| F | −0.0055 | 0.83 | 1.9e-4 | −0.416 |
| N | −0.0033 | 0.73 | 3.0e-3 | −0.340 |

Selection against γ is significant exactly and only where the realized shift
is large (F, N) — differential reproduction is a real component, not noise.
For the compositional side: `lineage_effective_n` (recorded from the
evolved-mode campaign onward, not in the older fixed-mode records) shows
populations at a median of 1.1–1.4 effective founder lines by t=4000, with
77–93% of runs at ≤2 lines — so compositional replacement via near-complete
lineage sweeps is a large share of any realized shift. The manuscript's
caveat stands (a full three-way partition needs dedicated tracking), but the
rebuttal answer is evidence, not a promise.

**Q4 — component-masked / randomized broadcasts.**
*Paper 2.* New treatment conditions; already in the follow-up plan. Nothing
in hand.

**Q5 — alternative resilience metrics.**
*ANSWERED — computed from stored trajectories* (`review_response_checks.json`;
harsh shock, 30 paired seeds; exploratory, raw p-values; pre-specified metric
remains recovery-time-to-90%). Population area-under-recovery-curve is at
ceiling in every condition (medians 0.990–0.992; F vs A p = 0.46, F vs N
p = 0.70): demographic recovery from the harsh shock is fast everywhere, so
this metric does not discriminate — and neither does fragmentation recovery
time (median 0 in all conditions, ≤1 nonzero paired difference). What does
discriminate is cooperation: post-shock cooperation mean F > A (+0.054,
p = 2.2e-3) and F < N (−0.081, p = 1.4e-4), with the same ordering for
post-shock cooperation variability. The conclusions the paper draws are
therefore not artifacts of the recovery-time choice: on the alternative
metrics, condition effects live in cooperative organization, not in raw
demographic bounce-back, which is what the manuscript claims. (A and B rows
are identical by construction — blind observation is dynamically inert under
paired seeds, a determinism check in itself.)

**Q6 — cadence with average dose held constant (rescale g with Δt).**
*Adopted into Paper 2.* The right controlled version of the cadence sweep:
vary Δt with g·(dosing rate) fixed, separating measurement frequency from
treatment intensity. Our existing Δt sweep (repository,
`dt_sensitivity_deltap.json`) established the confound this design removes.
Aliasing near ecological timescales is worth one sentence of the Paper 2
design discussion.

**Q7 — replay time-alignment and source independence.**
*Already answered in the repository.* `reviewer_checks.json` holds both the
one-receiver-per-source subset (n=15, r≥0.98) and the source-clustered
bootstrap; the paper cites both. Post-shock phase: source and receiver runs
share the shock protocol and the replay is index-aligned on the observer
grid, so both are in the same post-shock phase by construction — and the
passive-replay twin (scored on B) inherits the identical alignment, which is
what makes ΔP_R interpretable.

**Q8 — heavy-tailed or bimodal initial trait distributions.**
*Future work.* The ecology ensemble perturbs ecological parameters, not
trait priors; this is a genuinely untested axis. Fair to concede.

**Q9 — replicator-style approximation for I vs selection pressure.**
*Theory; future work.* The reproduction-neutral control's algebra
(P(reproduce|γ,b) = w_r/(W₀+γgD(b))) is the seed of exactly this
approximation — the marginal selection gradient on γ is ∝ −g·D(b) to first
order, which is I up to the ensemble average. Worth developing properly, not
worth improvising in a rebuttal.

**Q10 — diagnostics without untreated twins.**
*Discussion answer, no experiment.* Practical ladder, in decreasing power:
(1) synthetic inversion placebos — score the observed trajectory against
references it never received (the mirror of its own past states), as we do
for the passive-invert twin; (2) replay-style baselines — score against
another unit's realized signal stream, matched on phase; (3) pre-treatment
windows as within-unit twins where the signal has a start date; (4) the
mean-reversion decomposition — regress the alignment statistic on |s−0.5|
and shock-phase indicators before interpreting any residual as steering. All
four are instances of the paper's principle: an explicit passive baseline,
exact or modeled, before any alignment statistic is read as steering.

## Recommended posture

Do not reopen the manuscript. Q1, Q3, Q5, and Q7 now have complete
computed answers in this repository (`review_response_checks.json`,
`reviewer_checks.json`), Q2 has three stored partial results, Q10 has a
discussion answer, and Q4/Q6/Q8/Q9 are honestly assigned to the follow-up
study — several already in its pre-registered hypothesis list. The single
strongest rebuttal sentence available: *under conformist responses the same
passive-twin statistic yields a significantly positive ΔP in every seed —
the measure detects steering when steering exists, which is precisely what
makes the corrective regime's negative ΔP a finding and not an artifact.*
