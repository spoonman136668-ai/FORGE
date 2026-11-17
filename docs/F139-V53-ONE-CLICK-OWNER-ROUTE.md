# F139 V53 native original owner dispatch — development-only proposal

The original installed owner remains SHA 2ea68f93cbe6323aa6b0cbe99e47a32f0717b04c, event1839 376fe4921a41374ff47b1779c7d625bc3677ace91a052d6b64c790e390677c70. Source V53 is merged into protected main at a63ea00a9046bf107b59d64b3557ebd78c8f4157 with 8/8 post-merge qualification.

Design: a single **owner-authenticated** GitHub Actions workflow_dispatch invokes a detached original-Windows rehearsal first, and only on its success can a distinct same-run job attempt the existing one-shot source-only transition. The workflow must be pinned to protected main, exact prior event1839 and source, an authenticated original owner, first run attempt, and exact source-bound inputs. Keep the original scheduled task, SID, SQLite, negative receipts, isolated runner and the existing three independent lanes. No new controller, scheduler, queue, paid API, science first-use or routine owner comments. Any failed/uncertain write is HOLD, never replay.

This document is not execution permission. Before implementation and activation: verify source, exact ledger and original runner; freeze event/run provenance and workflow permissions; qualify full regression at exact PR head and main; require a user-authenticated GitHub Actions dispatch for live owner execution. Merely merging the workflow is NOT deployment.
