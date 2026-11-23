# RSH-04 — two original research artifacts: raw-byte integrity verified

RSH-03 merged into protected FORGE `main` as `d24bd22ea79fed9bb14a00b281d70ffd329601c0`, providing a source-qualified dual-mTLS, signed-witness **read-only FSA observation** interface. RSH-04 covers a different missing boundary: actual historical original evidence bytes, not just a six-lane source pointer or user-reported hash.

## Actual independently re-read original archive bytes (2026-10-24)

The independently pinned and previously frozen `reference/research-originals/20261013-dual-lane-manifest.json` identifies two historic original-source runs and raw SHA-256 digests. For each, a read-only GitHub connection independently confirmed the Actions workflow run completed `success` at the specified immutable source commit and verified the artifact ID/name from the run, including the GitHub-reported ZIP digest. The entire existing ZIP was then downloaded **read-only**, inspected as exactly one expected JSON member, and independently hashed. The ZIP and original raw JSON both matched the corresponding trusted historical pins.

| Lane | Original | Artifact ID | ZIP SHA-256 | Raw JSON SHA-256 | Preserved classification |
|---|---|---|---|---|---|
| Wingless | W-R39, run `38381594390`, source `ad3ade26204b14c372022bbed69dd59f91a3d02f` | `11803299743` | `9f221d1ce8c3cfaa863cb90c2b6c8d28b1458d78e90edb781b54bfa3d30521e1` | `33946f9f33d17539aadac42b05a4ebc4fb856dd3e5dafa8a4e43a11cdd5eb8e0` | `NATIVE_VERIFIER_BOUNDARY` |
| Yggdrasil | Y056, run `38381070805`, source `7e61f1c234c21ff0617075bea40c39afa5d11e89` | `11802529893` | `b792a89a708f4c76fb8842eee653dfe023598a9cde3b80ccb6621d36801b0af2` | `5ea4485afdeccd82e4d175eb01e56a696202d797a0136d21545ef568f7d9cd49` | **`NO_BENEFIT`** |

A machine-readable observation is retained at `reference/research-originals/20261024-rsh04-raw-integrity-receipt.json`. No original science artifact is copied into FORGE's public source; original research remains in its owner repository.

## Additive verifier

`researchfeed.VerifyOriginalArtifact` takes the **unmodified, untrusted six-lane source index**, an independently supplied frozen `OriginalPin`, separately retrieved `RunReceipt` identity, and the complete ZIP bytes. It validates the entire index first and compares the exact original lane/research ID/source repo/source commit/source path, historically expected outcome and optional reported SHA against the external pin. It requires completed/success at the frozen Git SHA, matching run/artifact identifiers, the pinned full ZIP hash, exactly one expected regular archive member, bounded decompression, exact raw-member SHA, unique JSON keys and unchanged classification. Partial, missing, forged, or oversized material fails closed.

**It never executes science**, performs network access, reads a credential, or grants archive CAS, controller dispatch, FSA first use or scientific acceptance. The output intentionally marks `evidence_zip_hash_verified` and `original_raw_hash_verified` when appropriate, while `original_bytes_authenticated=false`, `fsa_witness_authenticated=false`, `first_use_authorized=false`, `scientific_accepted=false`, and `dispatch_authorized=false`. A digest match against caller-supplied inputs is evidence integrity only; the Go interface does not authenticate the caller or independently acquire operator pins. The out-of-band historic Github artifact retrieval described above is a **separate read-only observation**, not deployment authority.

## What is NOT qualified

- **Independent FSA custody:** RSH-03 dual-mTLS/signed-witness *test fixtures* are source-qualified, but real operator-provisioned FSA endpoints/keys, independent service failure domains, signed archive-head and external witness receipt have not been produced for these original runs. This remains **NOT PROVISIONED / NOT VERIFIED**.
- **Scientific validation:** reproducible result quality, novelty, resource-matched competitors, causal ablations, and independently assessed evidence are not established by the ZIP hash or GitHub run conclusion.
- **First-use exclusivity:** a successful historical workflow run alone is not proof that no competing original execution occurred or that live first-use authority was held.
- **Current live six-lane intake:** F139, Wingless, Yggdrasil, other four research lanes, FORGE controller, queue, witness service, and private credentials remain unchanged.

## Next necessary evidence

Use the existing read-only FSA client against **already authorized, separately provisioned FORGE FSA and witness endpoints**, with externally sourced operator pins and exact archive-head/original-binding attestations. If real independently provisioned services are absent, retain the state `NOT_PROVISIONED`; do not fabricate a witness or introduce a new controller. Keep real original negative results and consumed histories immutable until independent science evaluation qualifies them.

Qualification uses the standard FORGE public Linux/Windows `.github/workflows/qualify.yml`, including F139 regression, Go tests/race/vet/build, and repo isolation. No direct CKB-plane dependency or access is introduced.
