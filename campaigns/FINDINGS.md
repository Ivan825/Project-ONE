# Project ONE — Consolidated findings across all campaigns (Aug 17, 2026)

**Evidence base: 970 runs.** Flagship (5 conditions × 50 paired seeds, mild shock),
harsh shock (5 × 30, 40% hub removal), sensitivity sweep (6 tokens × 20 seeds ×
3 feedback gains, harsh shock). All runs 4000 steps, deterministic, seed-replayable.
Statistics: Mann-Whitney U, Cliff's δ. Raw runs regenerable via `scripts/campaign.py`.

## Finding 1 — Measurement alone is causally inert (twice replicated)
Condition B (observed but blind) is trajectory-identical to A under paired seeds:
δ = 0.000 on every outcome, in both the flagship and harsh-shock campaigns. Only
the *broadcast* has causal power. This is the design's cleanest control.

## Finding 2 — The false story pulls reality toward itself (robust)
Story pull (macrostate movement toward the broadcast, counted only where the
broadcast differs from reality): F:invert exceeds noise at every gain tested
(g=0.2: 0.0103 vs 0.0014; g=0.8: 0.0079 vs 0.0028; g=1.6: 0.0086 vs 0.0060).
Flagship: δ = 0.76, p ≈ 6e-11; harsh shock: δ = 0.85, p ≈ 1.6e-8. The effect is
strongest relative to noise at LOW gain — a quiet, systematic lie out-pulls loud
noise by ~7×; at high gain noise itself starts to steer.

## Finding 3 — Populations fed lies evolve to stop listening (dose-response)
Global-sensitivity (heritable attention to the broadcast) is selected against in
proportion to how misleading and how loud the broadcast is. Δ mean trait, end−start
(harsh shock, g=0.8): no feedback −0.03 (neutral drift) · truth −0.10 ·
noise −0.30 · lie −0.42 (δ = −0.94, p ≈ 4e-10 vs baseline). The sweep shows a
clean dose-response: distrust of the lie deepens from −0.11 (g=0.2) to −0.45
(g=1.6), and even TRUE feedback becomes distrusted at high gain (−0.24 at g=1.6) —
a broadcast that jerks behaviour around too strongly is selected against even
when accurate. None of this ordering was programmed; it emerged from selection.

## Finding 4 — Not all lies are equal (new, from the distortion-mode sweep)
- **Inverted lie** (mirror of reality): the strongest self-fulfilling pull — it
  parasitizes the correction machinery, keeping every "deficit" signal active.
- **Crisis lie** (permanent alarm): weak pull (~0.002) — corrective responses push
  fragmentation AWAY from the alarmist story (self-defeating), while its constant
  cooperation-deficit signal drives cooperation to the highest levels observed
  (0.36–0.45). An alarmist lie mobilizes but does not come true.
- **Utopia lie** (everything is fine): **behaviorally inert** — identical to
  no-feedback on every outcome at every gain, because purely corrective response
  rules fire only on reported deficits. A flattering lie is equivalent to
  disconnecting the feedback loop entirely — and breeds no distrust, because
  attending to it is consequence-free.

## Finding 5 — Cooperation scales with feedback gain under truth
True feedback raises cooperation monotonically with gain: 0.27 (g=0.2) → 0.40
(g=0.8) → 0.49 (g=1.6) vs 0.19 baseline (δ up to 0.95). The loop acts as a
distributed homeostat repairing reported cooperation deficits.

## Finding 6 — Honest null: recovery time is feedback-insensitive
Even removing 40% of hubs, median population recovery is ~40 steps in every
condition (all p > 0.12). Resilience in this model is demographic (fast regrowth),
not informational. Reported as a robust negative result.

## Paper-ready headline
Short run: a false self-model steers the collective (Finding 2), with the
direction and force depending on the *kind* of lie (Finding 4). Long run:
selection removes attention to unreliable self-models (Finding 3). Together:
self-model feedback is a real causal channel whose credibility is itself an
evolving property of the system.
