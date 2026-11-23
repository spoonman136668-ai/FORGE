# FORGE R8 — source-inherited Shinka-inspired Pareto diversity (no live mutation)

**Source implementation scope: standalone nonexecuting historical replay.** This is a bounded native Go adaptation of specific algorithms from CKB-plane's preexisting [isolated R8 PR #296](https://github.com/spoonman136668-ai/ckb-plane/pull/296), exact source SHA `e1aa75d8a2428190df57c32e2e789130c4833917` and `proposals/evolutionary-portfolio-r1/portfolio_r8.py`.

The source design was inherited; neither the ShinkaEvolve runtime nor an autonomous prompt/code mutator was installed. FORGE `evoportfolio.ParetoAdvisory` is algorithmically analogous but **not yet an exact cross-language numerical differential qualification**; treat any divergence as a research gap, not a reason to change a frozen threshold.

## Scientific invariants

- Takes exactly the `evoportfolio.Frozen` and separately pinned `Digest(f)` used by the already-qualified historical baseline `Select`; computes that incumbent selection on the same source before the R8 advisory.
- Requires an independently pinned immutable Pareto policy: lane, original portfolio identity, **complete** historical lineage SHA, frozen baseline candidate ID, islands and per-island/global finalist caps; `fixed_before_screening=true` and `historical_only=true`.
- Every historical candidate must have one source/receipt/family/class/island/operator identity and up to four content-addressed parents. Retains **all** negatives, mixed and invalid nonfinalists. Missing/altered negative, orphan, duplicate, changed source or mismatched screen receipt invalidates the complete freeze.
- Historical score/cost nondominance is computed only among eligible candidates in their original island. A different eligible candidate dominates only when it scores at least as well at no greater sealed cost, with one strict improvement.
- Global budget, family/signature caps and finalist count **cannot exceed** the already-frozen original `evoportfolio.Frozen` values. No new screens, sealed trials, unseen results, hidden capacity, candidate reinitialization, or runtime mutation. A candidate scoring below the frozen baseline is not selected.
- Advisory reports the incumbent R1–R7 selected identities and total historical score alongside R8 selected identities, reserved sealed compute, complete archive and negative/mixed counts. `improvement_scientifically_established=false`, `mutation_runtime_activated=false`, `dispatch_authorized=false`, `scientific_accepted=false`, `accepted_ref_mutation=false` always.

## Qualification

Bounded native Go unit tests cover complete negative and invalid retention, exact external policy and portfolio identities, lineage order invariance, separately frozen baseline, score/cost Pareto, islands, sealed budgets, malformed genealogy, forged screen/source classes, island drift, forbidden oracle access, hidden capacity/permission expansion and no authority.

Require the exact branch Git tree's Linux full test/race/vet/build/isolation and native Windows full test/vet/build before merge. The original CKB draft code remains unchanged; do not replace that source or historic evidence.

## Still research-only

Prospectively freeze **before** new screening any candidate-generation/mutation mechanism; independently validate source birth and worker permissions, actual compute costs, negative-classification provenance, sealed cohort separation and discovery-gain uncertainty. Run paired frozen R1–R7 vs R8 trials on disjoint never-seen data, classify negative/mixed, and promote *only* if independently qualified; do not transfer CKB original custody or silently increase budgets. DGM/GenEnv and live Promptbreeder/Theta adaptation remain separate unqualified experiments.
