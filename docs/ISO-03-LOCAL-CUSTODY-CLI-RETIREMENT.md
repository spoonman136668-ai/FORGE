# ISO-03 — Retire the historical local CKB custody entrypoint

**Standing boundary:** FORGE has no operational dependency on CKB-plane. The sole permitted cross-project context bridge is optional, read-only, SHA-pinned Mind-Palace advisory retrieval; Mind-Palace grants no science authority.

## Finding

After ISO-02 retired the old network-based S14 workflow and history command, `cmd/forge-ckb-custody/main.go` still contained an executable, local-file-based inspector that could read installed legacy ledger files supplied on its command line. It was historically read-only and pin-verified, but even a read-only executable creates an inappropriate FORGE-to-CKB operational route.

## Correction

- Replace the executable with an unconditional failure that ignores all flags, paths, and caller-provided output writers. Its entrypoint never opens a file, contacts any server, emits a report, or claims research authority.
- Assert a permanent retirement sentinel in both native Linux and Windows required qualification, and reject restoration of the prior ledger library, file APIs, path discovery, network reads, and command execution in that entrypoint.
- Extend adversarial Go and Python checks to catch legacy arguments, nonempty stdout, attempts to restore ledger reads, removal of the sentinel, and re-import of the legacy CKB custody package.
- Preserve the `ckbcustody` standalone archival parser and Git history for historical reproducibility **only**. The parser is not FORGE authority and cannot be used by a live FORGE command. Removing historical archival provenance is neither necessary nor permitted.

## Boundaries and proof

No external private repo was contacted. No controller, Cloudflare service, Mind-Palace knowledge store, Wingless or Yggdrasil program was modified. No secret, Codex inference, original first-use, optimizer update, science approval, or dispatch is introduced.

This is a narrow defense-in-depth retirement, not proof that every historical name or schema has been erased or that live autonomous science has been authorized. Required exact-head Linux/Windows full regression and isolation checks are the acceptance evidence; no missing credentials can be substituted for them.
