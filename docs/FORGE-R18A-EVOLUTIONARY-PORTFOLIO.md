# R18A — FORGE-native bounded historical evolutionary portfolio

This isolated Go package adopts algorithmic ideas from exact CKB-plane public `main` source `9426a189cf3a3401a50d0455f366ff35d8944985`, specifically `proposals/evolutionary-portfolio-r1/portfolio.py` (R4–R7 shadow). It is **not** a copy of the CKB research controller, scheduler, acceptance process, queues or protected scientific source.

- An **independently supplied frozen digest** binds lane, epoch, historical cohort provenance, candidate identities, family, screening data, costs and caps.
- Every historical candidate including NEGATIVE, MIXED, INVALID and CONSUMED_INDETERMINATE is archived and retained verbatim; no class alteration. INVALID and indeterminate are never selected.
- Full historical screen cost is accounted, with a fixed global and per-family cap. A deterministic round-robin proposes diverse family finalists subject to the original sealed compute reservation. Results are advisory, never scientific acceptance, runner dispatch or new budget.
- Verifies input-order invariance, duplicated source/screen identity, stale SHA, class violations and budget drift.
- Does not infer unseen counterfactual outcomes, use heldout datasets, launch models or mutate preexisting policy/science. It is only R18A, **not** complete equivalence to CKB R4–R7 or full automatic CKB inheritance. Full behavioural differential tests and the remaining fixed CKB regression inventory are still required.
- Source-only public Linux/Windows qualification and one full regression are required before any further integration.
- Research F3 runs on a disjoint proposal/experiment branch, and CKB/KTRADE resources are not accessed.

Issues [#44](https://github.com/spoonman136668-ai/FORGE/issues/44) and [#23](https://github.com/spoonman136668-ai/FORGE/issues/23) track independent engineering and synthetic science respectively.
