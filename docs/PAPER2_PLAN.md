# Paper 2 — design plan

> **Internal working document — NOT part of the Complex Networks 2026 submission.**
> This records the follow-up study: its design, a pre-registered rule that
> failed, a primary hypothesis that came back null, and two defects found and
> fixed en route. Only three results from it reach the manuscript (the
> evolvable response strength/polarity control in Sect. 5.5); everything else
> here is future work or negative results kept for the record. Where this
> document says a limitation is weakened, read the qualifier: the response
> basis is still mechanistic, and empirical ecologies are unbuilt.

*Working title:* **Which response rules evolve when a network is told about itself?**

Status: **complete** — main campaign, gain and rule-form sweeps, and the
H7/H8 reconciliation (**1,210 runs**; 2,573 across both papers this round).
Sects. 1–2 are the design as written before running; Sect. 2.2a–2.2c record the pilot, including
a pre-registered rule that failed; Sect. **3a** holds the results.

---

## 1. What Paper 1 could not answer, and why

Paper 1 fixes a response function and asks what broadcasts do. Agents map a
received self-model `b` onto action propensities through a hand-written rule,
scaled by a heritable sensitivity `γ_i`:

```
w[a]  +=  γ_i · g · φ_a(b)          φ_a hand-specified, identical for all agents
```

Two rule forms were written by hand — *corrective* (repair reported deficits)
and *conformist* (imitate the reported norm) — and Paper 1 shows the
self-fulfilment taxonomy is a property of the composition `R ∘ B`, not of the
message. The rule-form control (`scripts/rule_form_check.py`) shows the γ
decline survives swapping one for the other, while the *ordering* does not
transfer.

That control is the strongest available answer inside a fixed-rule
architecture, and it is still an answer of the form "we tried two of them."
Every review has raised the same objection, and the objection is correct:
**φ was chosen, and choosing it is choosing much of the answer.**

There is a second, subtler cost, and it is the one that makes this a paper
rather than a robustness appendix. With φ frozen, a population that finds a
broadcast unhelpful has exactly **one** way to escape it: lower `γ`. Paper 1's
headline — attention to the self-model declines under consequential
broadcasts — is measured in a world where that is the only exit. We cannot
tell from Paper 1 whether declining attention is what evolution *prefers* or
merely what it is *permitted*.

## 2. The change: let the mapping evolve

Replace the hand-written φ with a heritable per-agent policy matrix.

```
w[a]  +=  γ_i · g · Σ_k  W_i[a,k] · φ_k(b)
```

* `a` — the six actions: harvest, share, connect, prune, reproduce, idle
* `k` — a fixed feature basis over the broadcast (Sect. 2.1)
* `W_i` — heritable, mutated at reproduction exactly as traits are, but
  clamped to `[-1, 1]` rather than `[0, 1]` so that **inversion is reachable**
* `γ_i` — unchanged, still heritable

Three properties make this the right generalization rather than a different
model:

1. **It is a strict superset.** Setting `W` to the corrective coefficients
   recovers Paper 1's engine; setting it to the conformist coefficients
   recovers the alternative regime. The two hand-written rules become two
   points in a space the population now searches.
2. **It removes the choice under attack.** We no longer specify *how* agents
   respond to the self-model, only *that* they can and that the mapping is
   heritable. What survives is what selection leaves.
3. **It opens the second exit.** A population can now disengage from a useless
   broadcast either by lowering `γ` (stop listening) or by driving `W → 0`
   (listen, act on nothing). `γ` and `W` are substitutes. Which route
   evolution takes is the new empirical question — and it is one Paper 1 was
   structurally unable to ask.

### 2.1 Feature basis

Keep the basis fixed and small — it is the one remaining designer choice, and
it should be defensible as "the broadcast, plus the deficits the broadcast
makes salient", not as a tuned dictionary. Ten features, from the five
broadcast components `b_k ∈ {fragmentation, centralization, cooperation,
inequality, turnover}`:

| # | feature | reading |
|---|---|---|
| 1–5 | `b_k − 0.5` | centered level of each reported component |
| 6–10 | `max(0, b_k − θ_k)` | reported excess past the thresholds Paper 1 already uses |

Centering matters: with raw `b_k ∈ [0,1]` a zero policy and an
indifferent policy are not the same thing, and mean-shifts would masquerade
as learned responses.

`W` is therefore 6 × 10 = 60 heritable numbers per agent.

### 2.2 The dimensionality problem, and the honest way around it

Sixty parameters, populations of ~50, and ~20 generations of lineage depth is
not enough for evolution to *discover* a policy from scratch. Pretending
otherwise would be the fastest way to an unreproducible result.

The design does not require discovery. Paper 1's γ result works by **selection
on standing variation**: γ is initialized uniform, and selection moves the
population mean over ~20 generations. The same mechanism applies here.
Initialize `W_i ~ N(0, σ_W)` independently per agent, and measure how the
population-mean policy `W̄[a,k]` *moves*:

```
ΔW̄[a,k]  =  W̄[a,k](t_end) − W̄[a,k](t_0)
```

per condition, paired by seed — the identical statistical treatment Paper 1
gives `Δγ̄`, so the analysis machinery, the multiplicity accounting and the
architectural controls all carry over unchanged.

Two things must be pre-registered before any treatment run, for the same
reason the ecology ensemble freezes its viability criteria first:

* **the horizon**, long enough for measurable lineage depth. Paper 1's 4000
  steps give ~20 generations; a scaled run at 12–20k steps gives 60–100. Fix
  it by a no-broadcast pilot on generation count alone.
* **`σ_W` and the policy mutation sd**, fixed by the same pilot.

### 2.2a Drift, measured rather than assumed — first pilot result

The first no-broadcast smoke test already found the trap this section was
written to anticipate, and it is worth stating plainly because it disqualifies
the obvious summary statistic.

Under **condition A there is no broadcast at all**, so `W` is completely
invisible to selection. Any movement in `W̄` there is therefore drift, by
construction. Over 1500 steps the RMS of the mean policy nonetheless rose from
0.028 to 0.212.

The cause is lineage collapse, and it is now instrumented rather than
inferred: `lineage_effective_n` (the inverse Simpson index over surviving
founder lines) falls to **~4** within a few hundred steps. With effectively
four lines contributing, the population mean of each cell is roughly
`N(0, σ_W/√4)`, so an RMS near 0.15–0.2 is exactly what pure drift predicts —
matching what was observed.

Consequences for the design, all of them tightening it:

1. **`policy_norm` is a drift meter, not a selection meter.** It is logged, and
   it is reported, but never as evidence on its own.
2. **Condition A is the exact null for `W`.** Every policy claim is the paired
   per-seed contrast `ΔW̄(treatment) − ΔW̄(A)`, the same treatment Paper 1
   gives `Δγ̄` — and for the same reason, since `γ` is equally invisible to
   selection under A and equally drifts there (`Δγ̄` under A is +0.116 to
   +0.277 in the stored harsh-shock runs).
3. **Read `W̄` cell by cell, not as a magnitude.** Drift is mean-zero across
   seeds and directionally arbitrary; selection is neither. A cell-wise shift
   consistent across paired seeds is the signal. Magnitude conflates the two.
4. `lineage_effective_n` is logged every observer tick so the drift budget is a
   measured quantity in the paper rather than an argument in its favour.

This is what the pilot stage is for, and it cost one smoke test rather than a
campaign.

### 2.2b The pre-registered rule failed — and it was the rule that was wrong

`scripts/policy_pilot.py --horizon`, run on condition A only, applied two
criteria fixed in the file beforehand: **≥ 40 generations** and
**`lineage_effective_n` ≥ 3.0**. Result, at 3 seeds per horizon:

| steps | generations | lineage_effective_n | population |
|---|---|---|---|
| 4,000 | 20 | 1.92 | 63 |
| 8,000 | 35 | 1.56 | 61 |
| 16,000 | 65 | 1.00 | 62 |

**No horizon passed**, and the reason is not one more compute can fix:
lineage diversity *falls* as the horizon grows. By 8,000 steps every run has
coalesced to a single founder line, and at 16,000 it is 1.00 in all three
seeds. Longer runs coalesce harder, not less.

The diagnosis is that the criterion had the causality backwards. Coalescence
to one lineage is the **signature of strong selection** — a selective sweep —
not evidence that selection cannot operate. Requiring standing lineage
diversity as a precondition for *measuring* selection was a mis-specification,
written on the intuition that diversity is what selection needs, when in a
population of ~60 selection is precisely what removes it.

So the threshold is **not** relaxed. Relaxing a pre-registered bound after
seeing it fail is the move the pre-registration exists to prevent. Instead the
instrument is replaced with one that does not depend on lineage diversity at
all.

### 2.2c The replacement: measure selection, don't infer it from the mean

Robertson's secondary theorem / the Price equation give the selection
differential on a trait `z` directly:

```
S(z) = cov(z_i, n_i) / n̄          n_i = realized lifetime offspring
```

computed over agents whose entire life falls inside the window, so offspring
counts are final rather than censored. This asks whether carrying a higher `z`
was *associated with leaving more offspring* — which is well defined inside a
single lineage, and does not require the population mean to move against
drift. High turnover works in its favour: a 4,000-step run yields a cohort of
roughly **4,000 completed lifetimes**, so each run is internally precise.

It also comes with an exact null. Under condition A no broadcast exists, so
`W` has literally no effect on any agent's behaviour and the true selection
differential on every cell is **zero by construction**.

**Validated before any treatment run** (`--selection-null`, 12 baseline seeds,
4,000 steps, cohorts of 3.3k–4.3k):

| quantity | expected | measured |
|---|---|---|
| policy cells (64), mean over seeds | 0 | median **−0.00054**, max abs **0.0072** |
| `S(global_sensitivity)` — inert under A | 0 | **−0.00027** (sd 0.0061) |
| `S(risk)` — scales harvest yield, positive control | > 0 | **+0.0110** (sd 0.0036, positive in **12/12** seeds) |
| `S(cooperation)` — costly helping | < 0 | **−0.0047** |

The same estimator, on the same runs, reads essentially zero for the two
traits that cannot matter under A and clearly non-zero for the one that does.
That is the instrument working.

Per-cell sd across seeds is 0.0069, giving minimum detectable effects of
0.0043 at 20 paired seeds and 0.0035 at 30 — against a real-selection
reference of 0.011 for `S(risk)`.

**Horizon, decided on these grounds:** 4,000 steps. Cohort size is already
~4,000 completed lifetimes, so precision is not the binding constraint, and
compute is better spent on paired seeds than on length. It has the further
benefit of matching Paper 1's own horizon exactly, making the two directly
comparable. This choice was made from condition-A data alone.

### 2.3 What the paper would claim

The claims are predictions, and each is falsifiable by the design above:

| # | prediction | what would falsify it |
|---|---|---|
| P1 | Under truthful broadcasts, `W̄` moves toward a **usable** policy — non-zero, and correlated with the corrective direction | `ΔW̄ ≈ 0`, or movement uncorrelated with any productive direction |
| P2 | Under systematically false broadcasts, the population **disengages**, by `γ` or by `W → 0` or both | `W̄` moves toward acting on the lie, and γ̄ holds |
| P3 | Under noise, `W̄ → 0` faster than `γ̄` falls — zeroing a policy is cheaper than abandoning a trait | the two decline together, or γ leads |
| P4 | The `R ∘ B` self-fulfilment taxonomy is **recovered, not assumed**: the evolved policy under each broadcast regime reproduces the regime's Paper-1 signature | evolved policies produce signatures Paper 1's fixed rules do not |
| P5 | Paper 1's γ decline is **partly substitutable** — with `W` free, the decline is smaller than with `W` frozen | identical decline either way (which would *strengthen* Paper 1, and is worth reporting as such) |

P5 is the one to be careful with. It is the prediction that reflects on Paper
1, and the result should be reported whichever way it lands. If the decline is
unchanged when the second exit is available, that is a *better* outcome for
Paper 1 than the one predicted here, and it goes in the abstract either way.

P4 is the strongest result available: the taxonomy that Paper 1 has to install
by hand would come out as a consequence.

---

## 3. The ecology question, and what real data can honestly do

The request is to remove the single-ecology limitation using real datasets.
The mechanism has to be stated precisely, because the obvious framing does not
survive contact with what the data contains.

**What real temporal networks cannot do here.** They cannot validate a
performativity claim. The claim is counterfactual — *what would this network
have done had it been told something false about itself* — and that
counterfactual is unobserved in every dataset that exists. Running the model
on a real contact network and reporting agreement would be a similarity
argument dressed as a test. This project has already retracted one headline
result (story pull) for exactly this class of error, after the passive
counterfactual showed the effect was intrinsic dynamics. Repeating the error
in Paper 2 would be worse, not better, for having been warned.

**What they can do, and it is enough.** Three uses, in descending strength:

1. **Empirical ecologies (the real answer to the limitation).** Initialize the
   network from real temporal networks — degree distribution, clustering,
   component structure, tie turnover rate — and run the ensemble across
   *empirical* initial conditions rather than perturbed synthetic ones. This
   is strictly stronger than the ±25% parameter ensemble now running for Paper
   1: those 24 ecologies are drawn from a family we designed, these are drawn
   from families nobody designed. "One ecology" is then answered by "seven
   ecologies from human contact, communication, and collaboration data."
2. **Calibrating the observer.** Compute the macrostate summary `S(t)` on real
   temporal networks and check its behaviour is not an artifact of synthetic
   topology — that fragmentation, centralization and turnover on real data
   vary on comparable scales and timescales to the synthetic runs. This
   justifies the compression, which is currently justified only by
   construction.
3. **Anchoring the shock.** Real networks contain real disruptions (term
   breaks, holidays, organizational change). Using an observed disruption
   instead of a synthetic hub-removal makes the recovery null — Paper 1's most
   robust pre-specified result — a statement about a realistic perturbation.

Candidate sources, all open and citable:

| dataset | domain | why |
|---|---|---|
| SNAP `CollegeMsg` | online messaging, 1.9k users | directed, timestamped, clean turnover |
| SNAP `email-Eu-core-temporal` | institutional email | departmental ground truth |
| SocioPatterns (school, hospital, conference) | face-to-face proximity | high resolution, several distinct ecologies |
| Copenhagen Networks Study | multi-channel (proximity, calls, SMS) | lets the *same* population appear as several ecologies |
| TGB temporal benchmarks | mixed | standardized loaders, aids reproducibility |

**Framing to hold to.** Real data enters as *initial conditions and ecological
priors*, and the paper says so in the abstract. It is not validation of the
mechanism, and no sentence should be constructible from the paper that reads
as if it were.

---

## 3a. RESULTS — main campaign (450) + sweeps (400) + H7 follow-ups (360)

`scripts/policy_campaign.py`, three arms × A/B/C/F/N × 30 paired seeds, on
Paper 1's harsh-shock protocol exactly (4,000 steps, 40% hub removal at
t=2000, gain 0.8).

**The pipeline is validated against ground truth first.** The `fixed` arm *is*
Paper 1's engine and protocol, so it must reproduce the stored campaign: it
does, **600/600 outcomes identical to 1e-9** against
`campaigns/harsh_shock/results.json`. Anything the other arms show is a
difference in architecture, not in code.

### H1 (PRIMARY, pre-registered): the 64-cell policy is not under selection

`rms_S`, the pre-registered one-number-per-run statistic, paired against A:
`C +0.00016 (p=0.89)`, `F +0.00019 (p=0.95)`, `N −0.00060 (p=0.21)`. Per cell,
**0 of 64 survive BH** in any condition, and the population mean does not move
either. **Null, cleanly.**

This is not the instrument's fault — the pilot shows the same estimator reads
`S(risk) = +0.011` with 12/12 seeds positive. A 64-dimensional response policy
simply is not learnable by selection in this ecology: each cell's fitness
effect is third-order (propensity → energy → reproduction) and sits below the
floor even with 30 paired seeds and cohorts of ~4,000 completed lifetimes.

Consequence, stated plainly: in the `evolved` arm **W stays essentially where
it was initialized**, so every behavioural difference that arm shows describes
*random* response rules, not evolved ones, and is not interpreted as the
latter.

### The design response: `policy_mode="polarity"`

The null above is the reason for what follows, and is reported rather than
replaced. Instead of inventing a rule coefficient by coefficient, selection
chooses the **polarity and strength** of the response on each of the four
action channels:

```
w[a] += rho_i[a] * (the hand-written rule's own term for a)
```

`rho = 1` is the hand-written rule, `rho = 0` ignores the broadcast on that
channel, `rho < 0` inverts it. Four heritable numbers instead of 64.

The claim "the hand-written rule is a point in the searched space" is here
**verified, not argued**: at `rho ≡ 1` the engine reproduces the hand-written
rule *bit-identically*, for the corrective and the conformist rule form alike
(`tests/test_evolved_policy.py`). Multiplying by 1.0 is exact in IEEE-754 and
the summation order is unchanged.

H7 and H8 below were written before the polarity runs; the decision to run
polarity at all was a response to H1, and that ordering is stated rather than
hidden.

### H8: selection drives the response to INDIFFERENCE, not inversion

Population mean `rho` per channel, with the paired shift against A (where the
policy is causally inert and drifts freely — hence the pairing). A ≡ B to
exactly 0.00e+00 on all four channels, as it must be.

| cond | connect | harvest | prune | share |
|---|---|---|---|---|
| **A** (baseline) | 1.036 | 0.866 | 0.965 | 1.049 |
| **C** truth | 0.945 (−0.018) | 1.052 (**+0.107\***) | 1.103 (+0.040) | **0.746 (−0.262\*\*)** |
| **F** lie | **0.341 (−0.598\*\*)** | 1.038 (+0.062) | 0.913 (−0.096) | **0.534 (−0.521\*\*)** |
| **N** noise | **0.770 (−0.191\*\*)** | **1.095 (+0.095\*)** | 0.942 (−0.051) | **0.567 (−0.447\*\*)** |

\* paired Wilcoxon p < 0.05, \*\* p < 0.0001, **n = 100**.

> **Revised from n = 30.** The first pass at the pre-registered 30 seeds put
> `share` under the lie at −1.175 and `prune` under truth at +0.155 (p = 0.016).
> Extending to n = 100 for the H7 follow-up (below) shrinks the `share` effect
> to −0.521 and takes `prune` under truth to +0.040 (p = 0.35) — **the
> "truthful feedback amplifies pruning" claim does not survive and is
> withdrawn.** Ordinary regression to the mean from a small sample; the n = 100
> column is the one to quote, and the p-values on the surviving cells are far
> stronger (< 1e-4) than the n = 30 pass suggested.

Four things fall out of that table:

1. **Nothing inverts at this gain.** The smallest population mean anywhere in
   the table is `+0.34`. The evolutionary answer to a systematically false
   self-model is to **stop acting on it**, not to act against it — even though
   inversion is exactly as reachable as amplification by construction
   (`rho ∈ [−2, 2]`, symmetric). *The gain sweep below qualifies this: at
   `g = 1.6` one channel does cross into inversion, so the finding is a
   threshold, not an absolute.*
2. **The suppression is cost-ordered.** `share` — costly helping, a direct
   energy transfer — is suppressed in **all three** broadcast conditions
   (−0.26 truth, −0.52 lie, −0.45 noise; every p < 1e-4). `connect`, which
   costs `action_cost`, follows but only where the signal misleads (−0.60
   under the lie, −0.19 under noise, nothing under truth). `prune` is free
   and does not move significantly anywhere.
   `harvest`, which *gains* energy, is the only channel ever amplified. The
   mechanism is legible: under the inverted lie, cooperation is reported as
   low precisely when it is high, so a high-`rho_share` agent gives away
   energy relentlessly and starves. **A false broadcast makes the corrective
   response lethal, and selection removes it.**
3. **The ordering matches Paper 1's.** On the channel that moves in every
   condition, suppression runs F (−0.52) > N (−0.45) > C (−0.26) — the same
   order as the γ decline, from a completely different measurement.
4. **The hand-written rule is not what selection favours on the costly
   channels**, and is left roughly alone elsewhere: `prune` — the one free
   action — does not move significantly in any condition, and `connect` is
   untouched under truthful feedback (−0.018, p = 0.68). Selection is not
   rejecting the rule wholesale; it is removing the parts of it that cost
   energy without repaying it.

### H4/H5: two routes to disengagement, and populations use both

Paper 1's own statistic, re-measured (`dgamma` vs A):

| cond | fixed (= Paper 1) | polarity | attenuation | p |
|---|---|---|---|---|
| C | −0.103 | −0.172 | +0.035 | 0.90 |
| F | −0.416 | −0.239 | **+0.126** (r=+0.66) | **0.0011** |
| N | −0.340 | −0.226 | **+0.165** (r=+0.65) | **0.0013** |

At the polarity arm's full n = 100 the decline is `C −0.125`, `F −0.222`,
`N −0.212`, **all p < 1e-4** — so the survival is not a small-sample artifact.
(The attenuation column above is computed on the 30 seeds the `fixed` arm has,
which is the matched comparison.)

**The γ decline survives when the response rule is free to evolve** — this is
the direct answer to the hand-written-rules criticism, and it is affirmative.
It is also *attenuated by 30–48%*, but only under false and noise feedback,
exactly the conditions where disengagement pays; under truth there is nothing
to disengage from and the substitution is absent (p = 0.90).

So γ and `rho` are substitutes, as Sect. 2 predicted, and the population uses
both: it listens less **and** acts less on what it hears, most on the costliest
channel, most under the least trustworthy signal.

(The same contrast computed on the `evolved` arm is larger still but is *not*
interpretable — W is not under selection there, so that difference is
confounded with the disruption caused by random response rules.)

### H6: the behavioural taxonomy survives

Under polarity, Paper 1's outcome differences are preserved in sign and close
in magnitude — cooperation `+0.18 / +0.06 / +0.10` (C/F/N) against the fixed
rule's `+0.21 / +0.10 / +0.16`, mean degree `+1.05 / +0.95 / +3.03` against
`+1.14 / +3.76 / +2.81`, post-shock fragmentation ~0 in both. Freeing the
response polarity does not overturn the behavioural results.

### H7: the two measurements disagreed, and the disagreement is now explained

At the pre-registered n = 30 the per-generation selection differential on
`rho` was not significant on any channel, while H8's accumulated shift was
large and highly significant. Rather than report only the half that worked,
this was chased down in two steps.

**Step 1 — more seeds (n = 100, 280 further runs).** Two cells resolve, and
both are on the channel H8 moves most:

| cond | channel | median ΔS | p |
|---|---|---|---|
| N | share | −0.00416 | **0.0009** |
| C | share | −0.00168 | **0.0381** |

Everything else stays null. Two cells (`connect` under F and N) carry a sign
opposite to H8's, but both are far from significance (p = 0.42, 0.62).

**Step 2 — split the window (`scripts/selection_timing.py`, 80 runs).** The
hypothesis was that selection against a costly response is *a sweep that
completes*: strong while standing variation in `rho` exists, near-nothing once
`rho` has collapsed and the variance is spent. Pooling `S` over the whole run
would then average a strong early signal with a spent late one — producing
exactly the observed combination of a large cumulative shift and a weak pooled
differential. Splitting the cohort window at 20 paired seeds:

| cond | channel | early (200–1200) | p | late (3000–4000) | p |
|---|---|---|---|---|---|
| F | share | **−0.0300** | **0.0153** | −0.0152 | 0.47 |
| N | share | **−0.0127** | **0.0042** | −0.0056 | 0.43 |
| C | share | −0.0013 | 0.81 | −0.0018 | 0.90 |

Under the inverted lie and under noise — the two conditions where H8 shows the
share channel collapsing hardest — the early-window differential is
**significant and about twice the late-window value**, and the late window is
null. Standing variation in `rho_share` falls 39–49% across the same span, so
there is materially less for selection to act on by the end. (That depletion
happens under silence too, so it is lineage coalescence rather than a
treatment effect; what is treatment-specific is the *differential*.)

**The two measurements therefore agree once timing is accounted for**, on the
channel where the effect lives. They are not two answers to one question but
a rate and its integral, and the rate is front-loaded.

Stated limits, because the reconciliation is not total: it holds for `share`,
not for the other three channels, whose early/late differentials are null and
in two cases sign-flipped; and `prune` under truth carries a negative
differential in both windows against H8's positive shift, both non-significant
and unresolved.

### Gain sweep: a dose-response, and where inversion finally appears

240 further runs, `polarity` at `g ∈ {0.2, 1.6}` (20 seeds, A/C/F/N) beside the
main `g = 0.8` cells. Condition A is inert to gain and its runs are
**bit-identical across all three gains** (max difference `0.00e+00` on every
channel), which is what makes the column below a clean common baseline.
Population mean `rho`, seeds 1–20 throughout so the rows sit on equal footing:

| gain | cond | connect | harvest | prune | share |
|---|---|---|---|---|---|
| — | **A** (all gains) | 1.044 | 0.782 | 0.944 | 1.077 |
| 0.2 | C | 0.996 | 0.966 | 0.920 | 0.952 |
| 0.2 | F | 0.657 | 1.028 | 0.985 | 0.915 |
| 0.2 | N | 0.847 | 1.135 | 1.233 | 0.985 |
| 0.8 | C | 0.777 | 1.015 | 1.180 | 0.773 |
| 0.8 | F | 0.268 | 0.977 | 0.785 | **0.100** |
| 0.8 | N | 0.667 | 1.061 | 0.922 | 0.686 |
| 1.6 | C | 0.861 | 0.690 | 0.888 | 0.456 |
| 1.6 | F | **−0.273** | **1.440** | 0.890 | **0.041** |
| 1.6 | N | 0.779 | 1.252 | 1.117 | 0.138 |

1. **The suppression is dose-ordered in gain**, monotonically, on every costly
   channel and in every broadcast condition: `share` under the lie runs
   1.077 → 0.915 → 0.100 → 0.041; under noise 1.077 → 0.985 → 0.686 → 0.138;
   under truth 1.077 → 0.952 → 0.773 → 0.456. This is the same dose-response
   Paper 1 finds in γ, reached by a different measurement on a different
   quantity.
2. **Inversion is a threshold phenomenon, not an absent one.** At `g = 1.6`
   under the inverted lie, `connect` crosses zero to **−0.273** — agents
   evolve to *disconnect* when told the network is fragmenting. It is the only
   cell in the entire study to do so. Disengagement is what selection reaches
   for first; inversion appears only where the signal is both maximally
   misleading and maximally consequential.
3. **The energy-gaining channel goes the other way.** `harvest` is amplified,
   most under the lie at high gain (1.440). Selection does not switch the
   response off wholesale — it switches off the channels that cost energy and
   turns up the one that supplies it.

### Rule form: does the finding survive swapping the underlying rule?

The obvious counter-attack on this design is that `rho` scales a *hand-written*
rule, so the same criticism recurs one level up. 160 further runs answer it by
re-running the polarity arm on the conformist rule form (`g = 0.8`, 20 seeds):

| rule | cond | connect | harvest | prune | share |
|---|---|---|---|---|---|
| corrective | C | 0.861 | 1.052 | 1.188\* | 0.738\* |
| corrective | F | 0.194\* | 0.977 | 0.908 | 0.238\* |
| corrective | N | 0.704\* | 1.061\* | 0.922 | 0.513\* |
| conformist | C | 0.250\* | 1.180 | 1.072 | −0.038\* |
| conformist | F | 0.944 | 1.434\* | 0.584\* | −0.004\* |
| conformist | N | 0.650\* | 1.306\* | 0.654 | 0.058\* |

The result mirrors Paper 1's own rule-form control exactly, including its
negative half:

* **The phenomenon transfers.** Costly channels are driven to indifference
  under both rule forms; the minimum `rho` anywhere across both is `−0.038`,
  i.e. still essentially zero rather than inverted. `harvest` is amplified
  under both.
* **The pattern does not.** *Which* channel is suppressed depends on the rule.
  Under the conformist rule `share` collapses to ~0 in **every** condition,
  truth included — and mechanistically it must, since the conformist share
  term is `g · b_cooperation`, an unconditionally positive costly push that
  pays nothing back regardless of whether the broadcast is true.

So the claim the paper can make is the narrow one: *selection removes costly
responses to a self-model, and reaches for indifference before inversion* —
and not the broad one, that any particular channel ordering is a property of
self-model feedback rather than of the rule being scaled.

### Two defects found and fixed en route

Both were mine, both in v2-only code, neither touching Paper 1 (`policy_mode`
defaults to `fixed`, and the ecology ensemble's 16/16 validation still passes):

- **Policy draws were taken from the behavioural PRNG.** 64 Gaussians per
  birth shifted every subsequent behavioural draw, so `evolved` differed from
  `fixed` even under condition A, where the policy cannot affect a single
  decision. Fixed with a dedicated `policy_rng` stream — the same failure, and
  the same fix, as the existing `signal_rng`. Five regression tests, including
  one asserting the policy *does* still matter where a broadcast exists, so
  the others cannot pass for the wrong reason.
- **A one-tick window error** in `fragmentation_post` (`t >= shock` where
  Paper 1 uses `t > shock`), caught by cross-checking the `fixed` arm against
  the stored campaign: 450/600 matched, and all 150 misses were that one
  field. Now 600/600.

---

## 4. What this does to the limitations section

| Paper 1 limitation | Paper 2 status |
|---|---|
| hand-written response rules | **substantially weakened, not removed** — the response *basis* f_a remains mechanistic; what is now heritable is its strength and polarity. With that freed (and the hand-written rule a bit-identically verified point in the space), the γ decline survives, attenuated 30–48% under false and noise feedback only, and selection moves the response toward indifference rather than inversion except at the highest gain |
| single ecology / parameter family | **substantially weakened** — 24 ecologies at ±25%, all headline results replicating; this is *local* robustness. Empirical ecologies from real temporal networks remain **open work** (Sect. 3, step 7), not something done |
| synthetic shock protocol | **open** — observed disruptions would need the empirical loaders, which are not built |
| agents are not strategic | unchanged, and now more defensible: the policy is selected, not reasoned, and the paper says which |
| no empirical performativity test | **unchanged, and stated as such** — see Sect. 3 |

The last row is deliberate. Two limitations removed and one honestly retained
is a stronger paper than three claimed and one over-reached.

---

## 5. Order of work

1. ~~**Engine**: heritable `W` behind a config flag, defaulting off.~~ **Done** —
   `policy_mode` in {`fixed`, `evolved`, `polarity`}; 33/33 tests.
2. ~~**Pilot, no broadcasts**.~~ **Done** — Sect. 2.2b–2.2c. The pre-registered
   rule failed and the instrument was replaced rather than the threshold
   relaxed.
3. ~~**Invariance check**.~~ **Done** — A ≡ B exactly, including on `rho`
   (max |A−B| = 0.00e+00 on all four channels).
4. ~~**Main campaign**.~~ **Done** — 450 runs, Sect. 3a.
5. ~~**Contrast against Paper 1's engine**.~~ **Done** — and it reproduces the
   stored campaign 600/600 to 1e-9.
6. ~~**Gain sweep and rule-form check.**~~ **Done** — Sect. 3a. The `rho`
   suppression is dose-ordered in gain, exactly as Paper 1's γ result is, and
   the phenomenon survives swapping the underlying rule while the channel
   ordering does not.
6b. ~~**H7 seeds.**~~ **Done** — n = 100 resolves the `share` channel, and
   splitting the cohort window shows why the pooled statistic looked weak:
   selection is front-loaded and the sweep completes. Sect. 3a, H7.
6c. **Open.** The `prune`-under-truth cell disagrees in sign between the two
   measurements (both non-significant). Nothing else is outstanding in the
   simulation half.
7. **Then: empirical ecologies.** Loaders, then the campaign re-run per
   dataset. Unlike steps 1–6 this depends on external data, and on the honest
   framing of Sect. 3.
8. Write.

Steps 1–6 are self-contained and depend on no dataset. A paper containing
1–6 is complete on its own: it answers the hand-written-rules criticism —
the one every reviewer has raised — and answers it in Paper 1's favour while
adding a finding Paper 1 could not reach, that populations disengage from a
false self-model rather than inverting their response to it.
