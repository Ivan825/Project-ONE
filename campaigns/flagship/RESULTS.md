# Flagship campaign — HISTORICAL first-pass analysis (superseded)

> **Note:** this file records the first-pass analysis (distance-based
> convergence metric, unpaired Mann-Whitney statistics) and is kept for
> transparency. It is superseded by the final paired analysis in
> `results.json` / `FINDINGS.md` and by the passive-counterfactual analysis
> in `passive_null_checks.json`.

**Design.** 5 conditions × 50 paired seeds, 4000 steps, hub-removal shock at t=2000.
Distortion mode for F: `invert`. Analysis exactly as pre-registered in `docs/PLAN.md`;
raw statistics in `results.json`. Raw run files (44 MB) are not committed; regenerate with
`python scripts/campaign.py --seeds 50 --steps 4000 --shock-step 2000 --out campaigns/flagship`.

## Headline findings

**1. Measurement alone does nothing — exactly.** Condition B (observed but blind) is
trajectory-identical to A under paired seeds (Cliff's δ = 0.000 on every outcome).
The instrument is causally inert until it broadcasts: a clean validation of the design.

**2. The broadcast changes the world, and its *content* sets the direction.**
Cooperation nearly doubles under true feedback (median 0.397 vs 0.179, p≈1e-16,
δ=0.96); false-inverted feedback more than halves post-shock fragmentation relative
to baseline (0.021 vs 0.042, p≈2e-5, δ=−0.50) — agents constantly told the world is
fragmenting over-connect it. Noise feedback also moves both outcomes: presence of
*a* signal matters, but C, F and N land in measurably different places, so
self-information is not reducible to stimulation.

**3. Flagship: the false story is self-fulfilling — with complete separation from
noise.** The drift-toward-broadcast index is positive for F (median +0.0032: reality
moves *toward* the false description) and negative for N (−0.0149), with perfect
distribution separation (δ = 1.00, p≈7e-18): every single false-feedback run drifted
toward its story more than every noise run. (C's negative value is definitional —
its broadcast equals the current state, so the gap can only grow between ticks —
which is why the pre-registered reference for this outcome is N, not C.)

**4. Null result, honestly reported: recovery time.** Median recovery to 90% of
pre-shock population is ~10 steps in every condition (all p > 0.27). The standardized
shock is too mild to differentiate conditions — the population re-grows almost
immediately. The follow-up campaign should use a harsher shock (larger hub fraction,
or simultaneous community removal) before concluding feedback doesn't affect resilience.

## Caveats for the paper

The agents' response rules encode how broadcast values shift action propensities, so
the *direction* of first-order effects is built in; the scientific content is the
system-level consequences (magnitudes, spillovers to non-targeted variables,
F/C/N asymmetries, the self-fulfilling index) and their robustness. Before
publication: sensitivity sweep over `feedback_gain` and `global_sensitivity`,
alternative distortion modes (crisis/utopia), and a harsher shock protocol.
