# V58 original-owner model-free failure-code projection (source-only)

Frozen main: `c06403c8b6035c6c7013866a7ea08cef1244b507` / Git tree `b7abf26f618654f330b55f510bfcc34d8916848a`.
Original workflow blob `39f189fde3a6fece791cd3a6ca7dd0517cb6b430`, proposed blob `da2abe072131358e411a82df170aa66b7f59b724`.
Engineering branch: `engineering/f139-v58-model-free-status-readonly-20261119`.

## Incident
Original F139 Windows owner reports repeated `MODEL_FREE_SEARCH_BLOCKED_FAIL_CLOSED`, but the V9 read-only status workflow strips the preexisting source-sanitized `failure_code`. PR #1819's native PR pagination drift is a separate incident; do not infer a shared cause. Source-only PR #1820 provides an independent bounded diagnostic helper, not a deployed original-owner change.

## Minimal projection
The **existing** `read-only-status` job, original event/owner/SID/source checks, source pinning, task, ledger, selectors, and startup log remain untouched apart from one exact-allowlist code projection. Python reads only the already-audited `SAFE_CODES` constants from checked-out FORGE source; four fixed fallback identifiers are explicit. An unrecognized or malformed value becomes `REDACTED_OR_MISSING`, and non-blocked records carry no failure code. The existing log tail is read-only; no model/network call is introduced.

## Original V40 invariant preservation
Existing `f139/test_v40_readonly_workflow_scope.py` also freezes the byte-for-byte original status prefix, SHA-256 `679e152e9be86b7399c75d247b31966f972a8d2196538b5729f8cf459d4ba063`. The V58-scoped compatibility update retains that check by asserting that removing only the exact V58 allowlisted projection restores the original frozen hash. It separately pins the resulting V58 prefix SHA-256 `b18d13cb82ddc7702117a215f251860fe2d2f4fd3b577c56a7cb775209d232e6`. No historical contract is erased.

## Security and acceptance
G145 branch-scoped original-owner admission binds protected base, the exact predecessor and successor workflow blobs, seven changed paths, original-author identity and existing GitHub event. G148/G156 retain complete Go/cross-platform checks with immutable base/tree. No generic workflow guard relaxation. Prove native Windows/Pwsh syntax and full Linux/Windows F139/Go/GenEnv regression at the eventual exact PR SHA; source-only static contract tests cannot substitute for a live-read-only original-owner witness.

This PR does not invoke the original owner, update policy #807, modify or read/write live SQLite here, install tasks, dispatch workers, run scientific first-use, merge, promote or claim learning/RSI. A separate original-source owner-authorized issue-comment run on main **after engineering approval and merge** would be needed to obtain the actual backend failure classification. Do not confuse static engineering PASS with live owner acceptance.
