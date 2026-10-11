# R19 — CKB → FORGE research-method and regression parity ledger

Status: **reviewed source inventory, NOT parity certification, migration, activation or authority**.

## Immutable comparison

- CKB-plane main: `9426a189cf3a3401a50d0455f366ff35d8944985`.
- FORGE R18H stacked source: `552889a90c0dfa53717b8b79e8d734c5f379d2ab`.
- This ledger does not imply FORGE is merged to main. CKB research, the current controller, Wingless, Yggdrasil and KTRADE remain untouched.

## Source-backed parity decisions

| Method / contract | CKB authoritative reference | FORGE candidate implementation | Finding | Mandatory gate |
|---|---|---|---|---|
| ShinkaEvolve-style family shortlist, capped screened and sealed budgets | `proposals/evolutionary-portfolio-r1/portfolio.py`, `test_portfolio.py` | `evoportfolio/selection.go` and tests | **PARTIAL**; deterministic family selection implemented, no complete behavioral differential | Same frozen fixture corpus, controls, selection and byte-for-byte projected decision comparison |
| Historical Dream-RSI gain per compute, no sealed-time learning | R1 README; `portfolio.py`; related CKB replay tests | `dreamrsi/replay.go`, `dreamrsi/optimize.go` | **UNVERIFIED equivalence**; FORGE has native modules but no R19 cross-repo protocol comparison | Replay identical negative/mixed histories, prohibit heldout leak; compare winners and budgets |
| Promptbreeder-style content-addressed lineage | CKB R1 README and proposal tests | FORGE `planner/plan.go`; historical `dreamrsi/lineage.go` | **UNVERIFIED**; no verified bounded mutation-operator parity | Parent/source/operator identity adversarial fixtures |
| ThetaEvolve fixed-state/learning-budget contract | CKB R1 README and prototype tests | No verified native R18 Theta contract | **GAP** | Freeze fixed capacity, no sealed-time update, no hidden growth; import test semantics only |
| R6 multi-batch, R7 scheduling / quota | `portfolio_multibatch.py`, `portfolio_scheduler.py`, `portfolio_r7.py`; matching tests | `evoportfolio/selection.go`, `progression.go` | **PARTIAL/GAP**; advisory cursor is not lane-local idempotent scheduler or multi-batch parity | Disjoint screen batches, max-per-lane compute, restart/interruption, no double selection |
| R196 one-at-a-time finalist progression | `R196-PROGRESSION.md`; `portfolio_progression_r196.py`, tests | `evoportfolio/progression.go`, `checkpoint.go` | **SEMANTIC DIFFERENCE**: FORGE accepts INVALID as completed checkpoint; CKB R196 explicitly blocks on INVALID; FIX REQUIRED | Change completion gate to forbid INVALID progression; focus test then full regression |
| R197 optional read-only CKB observer | `proposals/research-r197/R197-PORTFOLIO-OBSERVATION.md` | None; native FORGE `evoportfolio/handoff.go` only | **INTENTIONAL NONPORT**: preserve mechanism but avoid a permanent CKB adoption/observer loop | No shared live controller, no watcher installation |
| R198 independently pinned dual-lane provenance bridge | `proposals/research-r198/R198-PINNED-PORTFOLIO.md`; producer/tests | `evoportfolio/verify.go`, `strict_evidence.go` | **PARTIAL**: caller-supplied hashes, not externally trusted dual-lane manifest | Trusted pin custody from separate source, duplicate-key and traversal rejection, cross-lane source disjointness |
| Restart evidence, negatives, hash-linked recovery | CKB R1 README/R196/R198; portfolio handoff and science regression tests | `evoportfolio/handoff.go` through `strict_evidence.go` | **PARTIAL**; source-qualified synthetic verification, no persistent off-host CAS or protected custody | Negative/invalid preservation, bit-flip/missing/truncated/reorder, Windows platform and failure injection |
| Unseen source admission / scientific classification | `research/successor-builder/r214_source_policy.py`, `s58_s13_prospective_policy.py` and tests | F4 frozen science source and `dreamrsi/prospective` | **GAP**: synthetic pilot qualification must not be treated as authentic disjoint external source admission | Reproduce CKB source witness, identity/birth cutoff and scientific gate tests with independent original data |
| Durable once-only authorization and physical fault tolerance | Existing CKB research protections and FORGE FSA issue #20 | `pilotf4/eligibility.go`, `pilotf4/custody.go` | **BLOCKED**: tests and GitHub workflows are not independently controlled atomic CAS | Independently operated protected first-use, immutable raw retention, partition/fault qualification, signer custody |

## Parity acceptance invariants

- Qualify by immutable Git object identity and bounded affected interfaces; record known mismatch separately instead of changing thresholds or science retrospectively.
- Preserve positive, negative, mixed, invalid and indeterminate histories without relabeling; **INVALID blocks advancement**, is not a negative science outcome and cannot silently consume a finalist.
- No full portfolio parity promotion without a finite CKB fixture manifest, explicit coverage per subsystem, matched semantics, one complete FORGE integration regression and Windows acceptance.
- Do not import CKB live scheduling or authority; source-only migration cannot stop CKB research. Scientific activation additionally requires separate source admission and physical FSA trust.
- No recursive repo watcher or constant upstream polling; one-time immutable CKB handoff before retirement.

## Next executable repair

R19A is restricted to fixing the identified **INVALID progression** semantic mismatch with a preregistered regression that fails on the old source, then the full R18 suite on Linux and Windows. Continue beyond only after parity fixtures and protected evidence admission are real.

Evidence: the referenced CKB files and FORGE packages were directly inspected or their paths verified from the exact immutable source trees. A path match alone is not functional equivalence; every uncertain item is expressly labeled UNVERIFIED/PARTIAL/GAP.
