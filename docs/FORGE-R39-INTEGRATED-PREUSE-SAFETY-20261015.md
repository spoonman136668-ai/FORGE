# FORGE R39 — Integrated first-use safety contract (inactive)

R39 joins two separately source-qualified siblings, without rewriting their frozen implementations.

- R37 recovery, source 12cae834c4238c1eb6a5b89daa3e2a9bbe972ddd, qualified run https://github.com/spoonman136668-ai/FORGE/actions/runs/38795739918: exact recovery.go and recovery_test.go original blobs; a previously consumed uncertain/interrupted original cannot be replayed.
- R38 monotonic D1 candidate, source 1dcf4f58ee4d567dbd259e99e48e3b08270e2ab6, qualified run https://github.com/spoonman136668-ai/FORGE/actions/runs/38796349828: R35/R38 immutable unique original and monotonically increasing sequence and epoch guard with no Cloudflare install.
- R36 two-signer cryptographic source binding is unchanged and in the common ancestry.

The R39 acceptance workflow checks all three components together on exact head, native Linux/Windows, focused tests plus one Go full regression each (and one Linux race regression).

This is not proof of authentic external owner/witness key custody, current CKB owner epoch, externally authenticated D1 high-water, worker-side release fencing, genuinely pre-outcome randomization, a live original, or scientific gain. The code remains non-authorizing and draft.

Next authentic operational gate: existing authorized scientific owner provides independently authenticated current signer and first-use material, then its real original release path enforces exact source/experiment/worker binding before worker start; demonstrate one freshly approved experiment and independent review with automatic successor. No new controller, Cloudflare mutation, paid API/Codex review, accepted-ref promotion or disruption to current Wingless/Yggdrasil research.
