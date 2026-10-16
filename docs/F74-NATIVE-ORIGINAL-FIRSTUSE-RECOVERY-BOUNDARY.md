# F74 — Native FORGE first-use intake with authentic research-lane source, no execution

**Operational purpose:** Move FORGE-native original-admission source interlocks onto protected `main`, instead of repeatedly qualifying them on unmerged research branches or invoking the old CKB-plane research controller. This is the next small production-source integration after F73 verified a genuine protected-main GitHub OIDC identity. It does **not** grant protected scientific execution.

## What F74 actually integrates

`nativefirstuse.Prepare` reuses the existing FORGE `originalclaim.Claim` and `workerlease.Inspect` contract. It requires exact worker/intent/lane/current owner epoch correspondence, an unexpired lease, immutable first-use-risk semantics and two independently addressable Wingless and Yggdrasil cohort snapshot **shapes**. It preserves an exact rational logged selection propensity rather than rounding a Dream-RSI/Pareto six-arm assignment, rejecting any 0, nonreduced or invalid probability. It creates a deterministic, content-addressed non-authorizing candidate digest; the production-facing `AuthorizeLiveOriginal` **always refuses execution**, even if a caller forges a successful review.

**Important trust boundary:** The lane snapshots and claim passed into source tests are synthetic inputs. A syntactically sound ledger SHA is not proof that it captures **all** consumed, active and uncertain original first uses. Current trusted owner + signer custody, complete scientist source history, independent recovery and a Cloudflare at-start Worker permit are **not present**. This cannot legitimately become a scientific execution permit based on GitHub OIDC alone.

The same F74 workflow independently queries **actual current** Wingless/Yggdrasil public GitHub main configs, active research branch head, last reported research state and source-bound historical continuation-run metadata. This confirms the independent repo-local research lanes are still progressing without changing their state. Those source records do **not** attest complete original-first-use leases or independently selected scientific owner.

## Existing temporary backup choice

The owner-selected private `rbackup` repository remains the designated possible encrypted recovery destination, not an already qualified backup. The previously selected temporary **Cloudflare D1 Time Travel** recovery mode is accepted for non-mutating engineering/research preparation. It is short-retention, Cloudflare-dependent and **not** a privately exported or restore-tested independent backup. The existing Cloudflare R2 bucket-list probe was DENIED; no R2 purchase or extra encryption/signing keys will be requested just to continue safe work. No backup is exported, uploaded or restored in F74.

Production first-use claim migration / Worker deployment / scientific owner cutover remain blocked until the authorized native FORGE scientific controller can supply independently corroborated **current** Wingless and Yggdrasil complete original source-and-seed lease histories and explicit approved *new* original predecision, and the real installed Worker can enforce irreversible one-time claims with an operator-accepted recovery path. Historic S14, any ambiguous start and any prior consumed attempt remain non-replayable.

## Qualification and scope

F74 uses a narrow source-only Go package, focused positive/adversarial no-replay and identity drift tests, real GitHub API readback for both lanes and content-addressed nonsecret evidence; the protected-main PR must pass the repository's required independent Linux and Windows tests before merge. The post-merge main run independently establishes that this native fail-closed first-use code really ships on protected FORGE main.

No new controller, FSA service, research dispatch, rbackup upload, database write, signer credential, paid API, routine Codex review, or KTRADE modification. No interruption to independent Wingless/Yggdrasil research.

**Next operating dependency:** A **real current** prospective scientist owner custody source that emits a complete, independently pinned two-lane first-use ledger and a validated fresh pre-outcome policy assignment—then the existing Cloudflare at-start one-use Worker route and safe recovery. Do not treat a source-code test PASS as proof of this external evidence.
