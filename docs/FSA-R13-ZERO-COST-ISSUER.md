# FORGE R13 — $0 incremental-cost FSA checkpoint issuer (source candidate)

**Status: dormant implementation proposal; NOT deployed, authorized, or scientifically accepted.**

## What exists

The FORGE-native `fsaissuer` package implements the existing `fsaissuance.Issuer` interface. It requires:

1. An exact-scoped approval signed by a separately pinned FSA approval principal, including cohort, source witness, plan SHA, authority epoch, predecessor, proposed record and the FSA signing key identity.
2. A distinct, operator-pinned Ed25519 FSA public key, and an **injected**, separately controlled signing function. No private keys are generated, stored, read or supplied from FORGE workers.
3. An existing isolated authorization directory controlled by the FSA principal. A one-use `O_EXCL` attempt record is durably created **before** signing and is not removed on failure or restart.
4. Exact request equality. Invalid, swapped, forged, or unpinned requests cannot create the attempt. A signing failure leaves an unretryable uncertain first-use marker.
5. The existing `fsaissuance.CommitFirstUse` path still independently authenticates the external high-water and the complete archive, appends the original STARTED record once, verifies the issued FSA signature, performs one monotonic CAS and readback, and never dispatches science itself.

This is a real, executable, standard-library Ed25519 issuer component that composes with previously qualified FORGE primitives. It is *not* a second CKB authority, not a daemon or scheduler, and has no self-activation hook.

## Scientific and security limits

The local attempt directory is **not** an independent rollback-resistant store. A privileged local actor or disk restore can erase its entire history. An injected signer is **not** evidence of independent protected key custody. The approval signer must independently authenticate preregistration, origin, cohort and budgets: cryptographic verification alone cannot prove those checks happened. The issuer never verifies physical failure domains or archival retention. GitHub-hosted public CI validates source with synthetic keys only; no live FSA signing capability or private research data enters CI.

For any original FORGE autonomous science, existing issue #20 remains blocked until an independently trusted, protected high-water/identity/immutable evidence arrangement is demonstrated, including real fault recovery, and issue #25's independent source/causal/soak gates pass. Do not reinterpret $0 budget as permission to weaken them. The current CKB-plane research remains separate, with no new shared queue, scheduler, runner lease, accepted-ref mutation, or KTRADE impact.

## Qualification

Source foundation: integrated R1–R12 draft #38 at commit `87786526227e74004bd6acf4db7c12e30f9527f2`, tree `6bc3efa6d09f5473047c893d4fe9a2c7a5777354`. R13 modifies no existing files. Its dedicated GitHub-hosted Linux and native Windows gate validates the exact parent, four additive paths, focused issuer tests plus one full Go regression, vet and build; Linux additionally runs the full race detector. No cloud account, new equipment, paid services, deployment or source promotion is requested.

**Non-goal:** an operator approval signature does not confer execution authority. No original is eligible until existing controller/scientific authority boundaries, a separately proven FSA and explicit authorized activation are satisfied.
