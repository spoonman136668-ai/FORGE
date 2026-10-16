# F93 — Six-policy prospective matched-block design, optimizer-only

**Architectural scope:** FORGE scientific optimizer design only. Separate **FORGE Gate Advancement** owns owner/lease/first-use, unattended autonomy, real experimentation and Cloudflare authorization. **FORGE must not depend on or connect to CKB-plane.** Mind-Palace remains advisory, not scientific owner/witness.

## Why F93 is substantively different

F89–F92 use an individual **1/6 policy-arm randomization** design and a conservative per-lane Hoeffding/Bonferroni one-sided familywise lower confidence offset for 16 frozen candidate/control comparisons:

`1200 * sqrt(log(16/0.05)/(2*N))`.

With F90's 16,384 signed observation ceiling, a 5-point lower confidence offset is mathematically inaccessible. Do **not** turn such a historical negative into evidence the optimizer cannot work.

F93 is an **alternative future prospective trial**, not a re-labeling of F89/F90 observations. Each new research **block** consists of **six distinct, genuine research originals**, one per frozen selection policy (four controls, Dream-RSI, Shinka/Pareto), on an independently defined and preregistered *comparable task case*. The assignment/order of the six policies must be a **genuine independently randomized six-position permutation**, not a cyclic synthetic schedule, reused task seed, or outcomes arranged into attractive groups after measurement. Blocks must be independent, allocations and outcomes complete, budgets comparable and arm exposures noninterfering. A six-original matched block is not six free counterfactuals: all six must actually run under preregistered validity conditions.

If genuine independent blocks satisfy these assumptions, define `D_b = score(candidate in block b) - score(control in block b)`, with scores in `[0,100]` and `D_b ∈ [-100,100]`. The conservative **one-sided** familywise lower-bound offset for the same 16 planned contrasts is

`200 * sqrt(log(16/0.05)/(2*B))`,

where `B` is the number of independent complete **blocks per lane**. This is a *conditional mathematical result*, not a promise that the scientific problem supports safe matched exposures or that the owner executed any block.

| Target strict one-sided offset | Minimum complete independent blocks per lane | Distinct originals per lane |
| --- | ---: | ---: |
| <5 score points | 4,615 | 27,690 |
| <10 score points | 1,154 | 6,924 |
| <20 score points | 289 | 1,734 |

Using a conservative **16,384-originals-per-lane planning budget** for comparison with F90 yields at most **2,730 blocks**, with a one-sided offset of **approximately 6.50 score points**. That is sufficient *mathematically* to target a 10-point offset, but not 5 points. These are precision thresholds, not statistical power guarantees, source-reader compatibility, or invitations to execute thousands of originals. **F93 does not pass matched-block outcomes into F90's individual-randomization reader** and does not modify the F90/F91 statistical promises.

## F93 source qualification

- `optimizerstages/f93_matched_block.go` creates an immutable F89 two-lane-derived F93 plan, content addressed with SHA-256 and frozen matched-task, scoring, order-randomization and no-interference protocol digests. Plans are constrained to at most 2,730 complete blocks per lane in this source-only design.
- It validates six policy identities and six distinct positions per block, strict block-case/draw/receipt/outcome identifier reuse fences, class labels including NEGATIVE/MIXED/INVALID/INDETERMINATE/MISSING, and per-original compute costs.
- No matched comparisons are emitted for a lane containing a missing outcome; no imputed 0, no partial-complete-case IPS. Source-only matched score and compute contrasts are exact rational means, with conditional one-sided lower offsets.
- **Critical epistemic boundary:** Values, hashes, claimed random positions and block membership originate from supplied data; they do not prove source independence, genuinely random order, independent pre-outcome witness, a complete population, actual original execution, scientific acceptance or positive policy effects.
- Every plan and review leaves all scientific dispatch, accepted-ref, optimizer promotion, ThetaEvolve learning and Cloudflare mutation permissions **false**, including when synthetic tests contain positive differences.
- The F93 hosted gate re-reads **actual FORGE F92 source-only CI** [#38964701683](https://github.com/spoonman136668-ai/FORGE/actions/runs/38964701683) and runs adversarial and whole-repository qualification. It does not claim an actual prospective matched-block outcome.

## Scientific next step

The separately governed FORGE-native first-use and scientific custody authority would need to independently qualify that such matched comparisons are **scientifically feasible and ethical for both Wingless and Yggdrasil**, freeze the task source and randomization and no-interference rules before any outcome, execute authenticated first-use *once for every original*, preserve all failures/missing results, independently retain witness and cohort records, and accept the causal analysis. If the research design cannot support independent matched exposures, **reject F93 as a live design** and retain F91 or preregister a different valid method. A software green check never qualifies such a deployment.

Meanwhile Promptbreeder and DGM/GenEnv may continue untested novel-mechanism source work, Dream/Pareto cannot be promoted on historical replay, and ThetaEvolve cannot learn from fabricated accepted results.
