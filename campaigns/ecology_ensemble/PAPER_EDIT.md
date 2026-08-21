# Ecology ensemble — what to change in the paper, and what to add

Two separable things. **(1) is a correction the ensemble forces and should be
made whether or not the ensemble is reported.** (2) is the new paragraph, which
only goes in if the professor says fix-this-paper rather than write-a-new-one.

---

## (1) REQUIRED: rescope the densification claim

`cn2026_final.tex` line 407 currently reads:

> Broadcasts densify the network; false and noise feedback also flatten it.

Across 24 ecologies the truth arm is significant in **1 of 24** and even
correct-signed in only **16 of 24**, against **24/24** on sign for both
distortions. Replace with:

> False and noise broadcasts densify the network, and also flatten it.

Line 69 (abstract/intro region) carries the same over-scope:

> ... and broadcasts densify the network while false and noise feedback

Replace with:

> ... and false and noise broadcasts densify the network while also

**This costs no page space** — both replacements are the same length or
shorter. The sentence at lines 409–411 that gives the three numbers
(`+1.1` truth, `+3.8` lie, `+2.8` noise) stays exactly as it is: it is
correct as a within-campaign report, and the truth figure is already the
weakest of the three (r=0.49 against 0.80 and 0.72). Nothing else in
Sect. 5.2 changes.

---

## (2) OPTIONAL: the new paragraph, if Sect. 5.5 gets the space

Drop-in LaTeX, sized to one paragraph. Uses no new figure and no new table.

```latex
\paragraph{Does any of this depend on the ecology?}
The results so far live in one parameter family. We re-tested them in a
randomized ensemble of alternative ecologies, sampling $24$ candidates by
perturbing six ecological parameters---resource inflow and capacity,
reproduction cost, metabolic pressure, link cost and mortality---by
$\pm25\%$ independently. Viability was decided from the \emph{no-broadcast
baseline alone}, against four criteria fixed before any broadcast condition
was run (population neither collapsed nor pinned at the cap, non-degenerate
network at the shock, at least eight generations of lineage depth); all $24$
passed, with the tightest margin at $2.48$ against a floor of $2.0$. Each was
then run at A/B/C/F/N $\times\,10$ paired seeds under the harsh-shock
protocol ($1{,}200$ runs). Because the screen cannot see a treatment outcome,
no ecology could be admitted or dropped for producing the result we wanted.
Counting per-ecology paired contrasts, the cooperation gain under truth
($24/24$, median $+0.184$), the decline in evolved attention under the
inverted lie ($24/24$, $-0.396$) and under noise ($24/24$, $-0.258$), and the
observed-but-blind identity ($24/24$, every per-seed difference exactly zero)
hold in every ecology; the pre-specified recovery null holds in $24/24$ for
F and N and $22/24$ for C; and the ordering
$\text{F}\!\leq\!\text{N}\!\leq\!\text{C}\!\leq\!\text{A}$ holds exactly in
$21/24$ (median rank correlation $+1.00$). One claim does not survive and we
report it: densification under \emph{truthful} feedback is significant in
$1/24$ and correct-signed in $16/24$, against $24/24$ on sign for both
distortions---which is why Sect.~5.2 scopes densification to the distortions.
The perturbation produces recognizably different worlds (per-ecology spreads
of $2.5\times$ in mean degree, $2.2\times$ in cooperation, $1.9\times$ in
population) but not qualitatively different regimes: this is evidence of
local ecological robustness, not of arbitrary-ecology generality.
```

**Page cost.** ~13 lines of body text at the current settings. The paper has
zero slack, so this must be paid for. Cheapest sources, in order of least
scientific loss:

1. The Discussion speculation paragraph already trimmed once for the
   bibliography fix — a further 6–8 lines.
2. The `\itemsep` in the bibliography is at $-1.5$pt and **must not** be
   tightened further: every configuration reaching 12 pages by bibliography
   compression was verified to fuse glyphs at 400 dpi.
3. Do not shorten Sect. 5.2 or 5.5 to make room. Trading a verified control
   for a robustness paragraph is a bad trade at this venue.

If the space is not there, (1) alone is still required and is free.

---

## (3) Reproducibility sentence, if Sect. 6 mentions replay

The ensemble was computed across two machines and $31$ runs were computed on
both. Every state hash agreed across `x86_64`/Python 3.11.15/networkx 3.6.1
and `aarch64`/Python 3.10.12/networkx 3.4.2 --- different CPU architecture,
Python minor and networkx minor, bit-identical output. If the paper's
reproducibility claim currently says "across machines and operating systems",
it can honestly say "across CPU architectures, Python versions and networkx
versions". One clause, no page cost.
