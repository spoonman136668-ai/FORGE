# F139 V19 next gate: retain original spent free-model custody (READ ONLY)

**State:** new isolated dormant source candidate stacked on [#1040](https://github.com/spoonman136668-ai/FORGE/pull/1040), SHA `0abd467c5e98f472389cb9dae978a29e9685365e`. Not merged, not deployed. The original V17 Windows controller, its SQLite, existing issue #807, fixed finite free budget, candidate source targets, original `SingleOwner`, GitHub branch protection and N Research experiments are unchanged.

## Why a gate is needed

The V19 read-only terminal witness (#1040) can demonstrate genuinely verified new native training feedback, but original V17/V18 free-model request attempts have their own append-only custody. A request may already have been spent even if its provider timed out, model draft publication failed, a new FORGE SHA appeared, or the UTC day changed. V19 must not ignore this history when it eventually gains original-owner request authority.

The next helper `f139/nci04_v19_original_legacy_attempt_readonly.py` accepts ONLY exact original `Database` with held `SingleOwner` and invokes original `db.verify()` both before and after projection. It reads only original immutable event rows for `FREE_REASONER_ATTEMPTED`, `MODEL_DRAFT_ATTEMPTED`, and `MODEL_DRAFT_AUTHENTICATED`; it checks event types, dates, event ordering, previous event-head bindings, free-reasoner original scope recomputation, matching draft publication identities and duplicates. This is not remote-source proof or independent scientific acceptance. It never makes a provider request.

All `FREE_REASONER_ATTEMPTED` events remain spent regardless of publication success. Unresolved model draft writes are counted separately; their presence produces `BLOCKED_UNRESOLVED_ORIGINAL_MODEL_WRITE`, not a fresh-request permit. No sealed legacy event can be relabeled as a V19 attempt or as new evidence. Output is a minimal unprivileged, read-only snapshot of consumed scope hashes and per-lane attempt counts, with **no authorization**: `v19_provider_request_authorized=false`, `v19_attempt_history_authenticated=false`, `provider_requests=0`, `worker_dispatched=false`, `scientific_first_use=false`.

## Qualification and final blockers

- Negative fixture tests use the source's genuine SQLite event chain, original native admission and locally mocked model/provider; they exercise spending successful and ambiguous attempts, rejecting forged old events, refusing an unlocked or disabled original owner, and preserving no-replay on next UTC day. Hosted Windows/Linux runs must qualify exact head before even recommending this as a source candidate.
- **This does not install a V19 attempt ledger.** A separately specified V19 original-owner event schema, source transition, cold chain validator, V17/V18 historical migration seal and atomic pre-POST request reservation are still required before live inference. Every attempted request must consume its scope even on 429/timeout/ambiguous external write. Original finite V17/V18 allowance cannot be deleted, reset or reinterpreted.
- V18 [combined source candidate #1039](https://github.com/spoonman136668-ai/FORGE/pull/1039) remains independent and qualified, but real release-ref ruleset enforcement under GitHub administrator authority is still missing; no V18 owner cutover is justified until the actual immutable ref and owner proof pass.
- A green shadow cannot claim research is autonomous. That requires several **natural**, qualified, independently controlled Wingless and Yggdrasil native development cycles, correct negative handling, actual selection witnesses and cost/retention/transfer evidence.

**NO GO:** production changes, new controller/scheduler/queue, paid API, unsupervised provider inference, scientific first-use, protected main/ref mutation. Work remains an independent read-only design/qualification gate.
