# F139 V59 — Original Windows owner, authenticated read-only preflight

**Scope:** One existing, owner-initiated GitHub issue #807 comment on protected `main`. Reuses the qualified FORGE-CODEX-REMOTE Windows runner and existing V54 original-owner concurrency group; it does not add a controller, polling loop, queue, scheduled task, training invocation, backup or source release.

**Why:** Last original-host V9 read-only status at 2026-11-19 15:06 UTC authenticated original source `c06403c8b6035c6c7013866a7ea08cef1244b507`, event1864 SHA `e10be7151e19f2104ef2659ae04bef89b2711eea1659decb1477fd7354ff24ec` and 169 model-draft attempts/167 authenticated (two consumed uncertain). Existing V43/V54/V57 owner operations are pinned to older source/event preimages and MUST NOT be replayed.

**Contract:** Checkout and verify protected-main exact SHA; owner-only fresh issue comment, remote GET readback, policy #807 first-use false and model calls zero; check original admin/SID/one action/three triggers/unchanged install root; call the already regression-qualified `audit_frozen_original_readonly` through canonical `Database.open_readonly`. Emit only the sanitized source/head/negative-custody receipt. No SQLite writes, original task control, new scheduler/controller, paid API, remote publication or permission to activate.

**Only after full PR Linux/Windows qualification and protected-main regression PASS**, the owner may trigger one comment in the exact format:

`F139-V59-ORIGINAL-READONLY <protected-main-SHA> 1864`

Passing this diagnostic is still **not** an authorization to stop the original task, create a cold backup, run a detached rehearsal or change source. Those remain separately authenticated gates with first-use=false. A FAIL is preserved, not bypassed.
