# ISO-02 — Retire legacy FORGE-to-CKB execution surfaces

**Standing architecture:** [ADR 0002](ADR-0002-MIND-PALACE-ONLY-NO-CKB-DEPENDENCY.md). FORGE is independent. Mind-Palace is an optional, read-only, commit-pinned advisory context source, not a science authority.

## Verified source correction

The old `.github/workflows/forge-ckb-s14-readonly-history.yml` retained a manually dispatchable job that queried a separate private research-controller repository. It was a pre-isolation historical integration, but it remained live-capable after ISO-01. **ISO-02 removes the workflow entirely**; Git history retains its exact contents and provenance.

The corresponding `cmd/forge-ckb-s14-history` command now **always denies** without making network requests, even when a caller passes a token. Its Go tests prove the fail-closed behavior with no credentials. Historical Go-library archives and old evidence are left intact solely for reproducibility, not advertised as an operational connector.

The existing required Linux/Windows qualification executes `isolationguard/check.py` and its adversarial tests. ISO-02 extends that check from “no new direct source reference in the patch” to “no legacy workflow and no private repository URL anywhere in the current workflow tree.” It also verifies the retired command’s sentinel and denies reintroducing the prior network client. It does not purport to detect every possible intentionally obfuscated future route; independent review and package controls still matter.

## Explicit nonclaims

- No FORGE access to the other controller is requested or used to qualify this gate.
- No scientific first-use, owner/witness, dispatch, accepted-result mutation, optimizer promotion, Cloudflare write, or Mind-Palace ingestion is authorized.
- This is a removal/containment of legacy coupling. It is **not** proof that unattended scientific originals have started or that all historical code has been fully excised.
- All already-running independent Wingless/Yggdrasil scientific programs remain untouched.

**Acceptance:** exact PR-head Linux and Windows qualification; retired Go command's adversarial tests; forbidden workflow-negative tests; current active workflow-tree scan; independent branch/head integrity; post-merge protected-main qualification.
