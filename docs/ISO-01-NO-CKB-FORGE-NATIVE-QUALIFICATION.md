# ISO-01 — machine-checkable FORGE/CKB-plane isolation

**Operator boundary:** FORGE and CKB-plane stay disconnected. Direct, bounded, commit-pinned, read-only Mind-Palace advisory retrieval is the sole cross-project context bridge. See `AGENTS.md` and `docs/ADR-0002-MIND-PALACE-ONLY-NO-CKB-DEPENDENCY.md`.

This gate converts the standing separation instruction into an automated check on the **existing required Linux qualification job**. It does not create a new scheduler, runner authority, Cloudflare resource, science admission policy or scientific original.

### Behavior

1. Require that `AGENTS.md`, ADR 0002 and README continue to state the operator's explicit isolation rule.
2. On the checked-out exact CI head, inspect the Git diff against the **first parent**. On a GitHub PR merge check this is its base; on a protected-main merge this is the previous main; on an ordinary branch push this is the previous commit.
3. Reject **new added source/config/workflow lines** that reference the private CKB-plane GitHub namespace, including simple quoted/split and hexadecimal/unicode-escaped spellings. Fail closed if Git identity, ancestry, patch or source policy cannot be read.
4. Preserve legitimate historical schema labels and provenance notes, including documentation in `docs/`, `reference/` and `archive/`. Do not rewrite existing frozen scientific receipts. The gate's own focused tests and checker are exempt from the literal grep because they must contain hostile example strings, and are covered by adversarial tests and engineering review.
5. Run seven adverse-case unit tests before the standard Go tests/race/vet/build. The pre-existing required Windows check remains unchanged.

This is defense-in-depth; static source checks cannot detect all possible dynamically constructed dependencies, and they do not establish future scientific authority. New FORGE-native owner/witness, original first-use, accepted science and Cloudflare permits remain separately gated. Any attempt to reintroduce private CKB-plane readback must be redesigned natively rather than permitted via new credentials.

**No effects:** no CKB API call, no credentials, no Mind-Palace writes, no Wingless/Yggdrasil mutations, no optimizer activation, no live deployment.
