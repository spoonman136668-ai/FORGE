# F92 — prospective six-arm optimizer precision, not speculative optimizer gains

**Workstream:** FORGE optimizers only. Autonomy, controller continuity, original dispatch, Cloudflare recovery/deployment and scientific release remain the independent FORGE Gate Advancement workstream. **No CKB-plane integration**; Mind-Palace is optional pinned read-only context, never a scientific owner.

## Genuine issue closed by F92

F91's frozen comparison estimates **16** total policy-arm contrasts: for each of Wingless and Yggdrasil, Dream-RSI and Shinka/Pareto against four distinct frozen research-selection controls. The source-only F90 reader currently accepts at most **16,384** signed observation records *per lane*. Its bounded score is in **[0,100]**.

F91 uses a conservative Hoeffding/Bonferroni simultaneous 95% *conditional* half-width, based on the exact **1/6** policy-arm randomization probability and score range:

`h(N)=1200*sqrt(log(16/0.05)/(2N))`.

At N=16,384 in a lane, `h≈15.9214` score points; an observed margin of only five points cannot exclude zero using that prespecified bound. The strict mathematical observation counts to achieve **half-width smaller than** selected target margins are:

| Target half-width | Minimum observed originals **per lane** | Within F90 16,384-row cap? |
| --- | ---: | :---: |
| <5 score points | **166,128** | No |
| <10 score points | **41,532** | No |
| <20 score points | **10,383** | Yes, mathematically |

These are conditional **precision requirements**, *not* sample-size/power guarantees, prediction of scientific improvement, permission to run that many experiments, or a replacement for real independent causal evidence. Meeting h<20 does not imply a future estimated margin exceeds the bound. No outcome data are used for this design calculation.

## F92 engineering

`optimizerstages/f92_precision_budget.go` exposes a frozen `PlanF92Precision` with:

- Both lane-specific F89 design digests and distinct owner source/preregistration/slate/source-family identities.
- User-selected precision target and a bounded *planned* number of observation records per lane, never exceeding the qualified 16,384-row F90 reader.
- Strict minimal sample requirement from the exact F91 uncertainty formula, the half-width at both planned and source-reader maximum, and truthful mathematical feasibility or need for a separately validated larger reader or **preregistered** alternative estimator.
- Domain-separated SHA-256 content identity. Re-hashing a modified output, changing the policy epoch or changing any eligibility/authority flag fails validation.
- Unconditionally false real science/first-use, witness/owner, causal improvement, Dream/Pareto authorization, ThetaEvolve learning, Cloudflare writes and scientific dispatch flags.

No synthetic source records, fake first-use witnesses, invented scientific wins, new controller, GitHub scheduler, paid API or live infrastructure change. No modification of F91's frozen statistical method. F92 deliberately **does not** silently lift F90 to 166k records; doing so could exhaust hosted runtime/resources, weaken the existing source reader and authorize no original research. A future bounded streaming intake or a separately qualified more efficient preregistered estimator is another legitimate optimizer engineering gate, to be evaluated under actual budget and independent science controls.

## Qualification and next scientific work

The F92 workflow reads back [the genuine F91 GitHub source-qualification run](https://github.com/spoonman136668-ai/FORGE/actions/runs/38962995679) at SHA `714413a8696369593568e4227bf1f5c0cf66919d` and runs adversarial F92 Go tests, five optimizer package tests, complete repository test/vet/build and required Linux/Windows protected checks.

**Scientific stop line:** This source/precision work does not claim that a real prospective experiment exists. Before assessing Dream-RSI/Pareto scientifically, the native owner track must independently demonstrate preregistered, pre-outcome randomized allocations, complete once-only originals (including negative, missing, mixed, invalid), independent admission and sufficient statistical precision. ThetaEvolve stays on frozen/no-learning policy until independently accepted new results arrive.

**Next optimizer option:** With the same F91 frozen estimand, explore a rigorously preregistered, bounded-variance or matched-baseline evaluation protocol and genuinely novel proposals from Promptbreeder/DGM/GenEnv *without* moving scientific authority into this workstream. A tighter confidence bound requires an independently established statistical design, not cherry-picked outcomes.
