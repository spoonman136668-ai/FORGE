# Dream-RSI source adoption — verified preexisting R1, not a live optimizer

FORGE now contains the complete original standalone `dreamrsi/` and `cmd/forge-dreamrsi/` source from its **preexisting** qualified-proposal branch `proposal/dreamrsi-r1-20261011` at exact Git commit `e2502dfb5e607363c6e758419d8d509d1a3bd5c6`. Each of nine imported Go source/test files was transferred without semantic rewriting and its original Git blob identity is retained in the PR's file history.

This is **not** another independently designed replacement for CKB-plane; it is a bounded adoption of the user's already-developed research innovation.

## Capabilities actually implemented in the imported code

- Independently SHA-pinned, Ed25519 signed, chronologically verified original exploration histories with candidate menus, cohort/source/receipt identities, original outcome classifications (including NEGATIVE, MIXED, INVALID, CONSUMED_INDETERMINATE), compute and logging probabilities.
- Explicit separation of observational from audited randomized decision histories; reject unsupported model-based counterfactual improvement. Replay with bounded inverse propensity scoring and no invented missing option outcome.
- Deterministic policy mutation and content-addressed parent/policy lineage, finite generations and populations, bounded replay counts/evaluation budgets, strict train/validation separation and no hidden capacity.
- Independently pinned **separate sealed-holdout assessment** that never enters the optimizer's mutation/selection API.
- Immutable local policy record journal and restart observation; not an external FSA authority, controller, queue or production deploy.
- A bounded read-only `forge-dreamrsi` CLI that requires operator-supplied signed histories and exact immutable trust pins.

## Safe integration boundary

The lighter `evoportfolio/policy_replay.go` previously merged via #153 is an **offline historical policy comparison** exercised with explicitly synthetic train/holdout fixtures. The newly adopted `dreamrsi` implements a **strictly stronger authenticated and randomized decision history path**. They must not be conflated: the shallow fixture selection is not scientifically causal and is not the authority to enable mutation. No real signed randomized propensity histories have been provisioned to this CLI, so a real prospective optimizer selection or benefit claim is **NOT YET QUALIFIED**.

No sealed samples, real first-use original, result promotion, independent run scheduler, CKB old-owner mutation, KTRADE broker or unprivileged user file are touched by this adoption. Preserve the advanced R2–R12 branch work, but promote only after independently pinned, source-clean individual integration; do not blindly merge all older workflows or authority prototypes.

## Acceptance

One complete source qualification against the current FORGE Git tree, including Linux full tests/race/vet/build and native Windows full tests/vet/build and exact immutable merge-tree verification. The imported package tests check negative/invalid evidence, source edits, signing tamper, fixed budgets, unsupported propensity, temporal and sealed holdout leakage, deterministic mutation, local no-overwrite and crash recovery.

Future real-operations gates are issue #25: genuine historical decision-time propensity and outcome custody, verified immutable signed records, strict source/cohort disjointness, separately frozen prospective holds, science-authorized once-only review, and independently qualified real discovery efficiency comparison. Never claim improvement from synthetic performance.
