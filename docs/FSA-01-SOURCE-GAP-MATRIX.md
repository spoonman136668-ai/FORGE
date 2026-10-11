# FSA-01: source-bound gap matrix (read-only)

Baseline: FORGE main `c51578b6ed88205069a90ea12efc45b2057384b2` (R19L).
Qualification: [hosted run 38183143909](https://github.com/spoonman136668-ai/FORGE/actions/runs/38183143909) — Linux and Windows PASS, qualification-only commit `f0c9d700066eee3651b5f579c6c0c4ece3f3e072` pinned to that exact parent.

This matrix catalogs **existing source-only capability** versus **still-missing independent execution authority**. It is neither an activation checklist auto-approval nor scientific acceptance evidence. Do not turn a PASS in this document into permission to run science.

| Boundary | Existing immutable source | Verified capability | Remaining independent evidence or implementation | Disposition |
|---|---|---|---|---|
| Candidate proposal | `contracts/protocol.go` | Bounded quarantine-only proposal validation, immutable source/cohort/preregistration pins and explicit denied privilege flags | Scientifically qualified frozen protocol and independent eligibility decision | BLOCKED |
| Archive lineage | `researchlog/`, `privatearchive/` | Source-only hash-chain, original-evidence retention interfaces | Independent source birth / holdout attestation; deployed isolated durable archive | BLOCKED |
| Signed head | `fsahead/verify.go` | Ed25519 authenticity and exact predecessor checks against full archive | Externally provisioned signer custody and independently anchored identity | BLOCKED |
| Checkpoint protocol | `fsatrust/checkpoint.go` | Interface for separate monotonic CAS backend, indeterminate handling, authenticated readback and read-only recovery | Truly independent protected backend / binding / restart validation | BLOCKED |
| Local receipt primitive | `fsaanchorstore/store.go` | Write-once local receipt implementation with pinned genesis and identity validation | Physical independence and external monotonic protection. Local store explicitly **does not** satisfy this | BLOCKED |
| Independent runner/queue | Not present in approved source-only architecture | None claimed | Separate FORGE-only durable queue, leases, failure-domain isolation, no CKB/KTRADE jobs | BLOCKED |
| Scientific primary | None activated | None claimed | Frozen preregistration, disjoint source/cohort, one-shot intent, start witness, terminal evidence, negative/mixed preservation | BLOCKED |
| Cross-system isolation | `docs/ADR-0001-FORGE-SCIENTIFIC-AUTHORITY.md` | Architecture establishes disjoint ownership | Fault injection + concurrent shadow validation proving no CKB/KTRADE interference | BLOCKED |
| FSA controlled activation | Not provisioned | None | Independent acceptance and explicitly authorized controlled cutover | BLOCKED |

## Delta sequencing

1. Add **non-executing** deterministic preregistration and source eligibility verification contracts. Fail closed on mismatch, reuse, missing provenance, ambiguous start, and lane collision. Keep no dispatch API.
2. Verify bounded interfaces with `contracts`, `researchlog`, `privatearchive`, `fsahead`, `fsatrust`; reuse unchanged source only at exact identity.
3. Qualify on GitHub-hosted Linux and Windows; focused tests, affected interfaces, one final full regression, vet, build, Linux race.
4. Separately develop and qualify FSA backend / runner / scientific admission in distinct authority work, only after approval. Never infer authority from this matrix or a green CI status.

## Non-negotiable constraints

No FSA activation, science dispatch, signer provisioning, queue consumer, accepted-ref update, CKB/KTRADE/mind-palace writes, credential access or historical-result reclassification. The R19L qualification does not provide these permissions.
