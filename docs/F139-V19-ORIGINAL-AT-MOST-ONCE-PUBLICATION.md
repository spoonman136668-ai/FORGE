# F139 V19 — Original-owner single-attempt publication custody

**DRAFT, source-only, unmerged, not activated.** Exact parent: qualified V19 #1050 commit `d304167b49181a755320aa99b522321fe4d9bd16`.

This bounded gate joins the cold-authenticated V19 model proposal and the qualified original-owner no-write publication preflight to the **existing** original owner `MODEL_DRAFT_ATTEMPTED` / `MODEL_DRAFT_AUTHENTICATED` ledger events and bounded `_write_draft` implementation. No new publisher, scheduler, queue, runner, task, credential source or generic command execution is introduced.

## Safety contract

1. The caller must already hold original F139 `SingleOwner` and present the original owner witness. The function is **not connected to `run_once` or scheduled task**.
2. Run the existing V19 no-write authenticated preflight twice and require identical manifests, exact original validated-ledger head, source SHA and immutable candidate bytes. The previous spend of a single free-model request is never repeated.
3. Under original SQLite `BEGIN IMMEDIATE`, cold verify source and head, no active/READY task, owner witness and previous publisher history. Append exactly one historical-schema `MODEL_DRAFT_ATTEMPTED` event and commit **before any remote GitHub mutation**.
4. Only the original bounded publisher's injected `_write_draft` may attempt the single target-file draft PR. It requires an authentic owner, one exact commit and one allowed native file. Unknown POST/ref/PUT/PR responses consume the attempt forever; there is no retry and no duplicate fallback.
5. After an authenticated draft response, only append `MODEL_DRAFT_AUTHENTICATED` when the immediate original attempt still occupies the current SHA-linked head, under the same owner lock.
6. Extend the original cold `Database.verify` to validate V19 attempt ancestry/identity, deterministic branch, historical schema, terminal-pair adjacency, and immutable no-replay flags. Historical V17/V18 publication events are unchanged.

## Qualification boundary

New tests create only disposable original SQLite, fake predecessor free-model transport, fake public Git GETs and monkeypatched fake writer. They assert that the attempt is visible to a separate cold SQLite reader **before** the simulated first remote write, timeout remains unreplayable, revoked owner and changed source/policy fail closed, forged remote output cannot authenticate, and history is retained. They make no real model/GitHub provider request.

Require focused original native tests and all Linux/Windows F139, public Go+Python, and hosted F139-D workflows on the exact SHA. Retarget to stacked #1050 after evidence is complete. **Do not merge, dispatch, publish a real model draft, grant scientific first-use, change accepted refs, or cut over the live Windows controller from this PR.** Any approved future V19 release requires independent original-owner runtime qualification, protected release source, explicit custody check and a single final full regression.