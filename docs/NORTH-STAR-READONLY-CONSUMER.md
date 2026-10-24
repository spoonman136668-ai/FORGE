# FORGE — Unified North Star read-only consumer (source-only preflight)

**Owner goal:** one shared Mind-Palace memory, one FORGE intelligence-research operations hub, independent Wingless/Yggdrasil/BIO/Optimizer/Mass Research/Language Research lanes, and one owner-directed North Star. This gate advances **source-pinned recall validation**, not live controller authority.

## Implementation

- `researchsteer.ReadPreview(ctx, source)` accepts the exact existing `mindcontext.Source` interface, resolves one Mind-Palace `main` commit and requires an immutable 40-character SHA on the one governance file. `mindcontext.GitHub` now permits this one additional fixed file through its existing authenticated, bounded, GET-only Contents transport.
- It validates owner authority, exactly one shared Mind-Palace repository, FORGE as the intended *future qualified* research operations/scientific admission hub, independent research lanes, the no-CKB-plane constraint, broker isolation, and non-disruption of frozen and in-flight work.
- It yields a bounded advisory preview with commit SHA, content SHA-256, policy ID and revision. It exposes **no** dispatch, queue, worker lease, scientific acceptance, protected merge, checkpoint, intake-writer or live-steering operation.
- Failure to retrieve the future policy at an accepted Mind-Palace commit or to validate any mandatory guard rejects **this optional new preview only**. No existing research worker or experiment is stopped or restarted. Existing authorized FORGE work remains independent.
- The policy is presently on a separate Mind-Palace draft PR (#101), not `main`. A real preview from production `main` is therefore **not available yet**. Do not insert a fictional source file into public CI or use private tokens in qualification.
- `researchsteer/reader_test.go` runs against synthetic in-memory source fixtures only. These prove contract validation, not an authenticated private read, real cross-agent steering, or scientific gains.

## Test and improvement acceptance

Focused checks: `go test -count=1 ./researchsteer ./mindcontext`, `go test -race -count=1 ./researchsteer`. The existing `.github/workflows/qualify.yml` already executes a complete Go regression, race pass, vet and build on GitHub-hosted Linux, plus full Windows native test/vet/build. **No workflow or controller is added by this gate.**

Before enabling actual research steering:
1. Qualify Mind-Palace source policy and accepted version in the protected repository. Ensure revision ordering and issuer/source custody cannot silently be changed.
2. Authenticate a private read with FORGE's already-approved read-only credential; pin and record the exact source commit and Git blob provenance, with no secret material in logs.
3. Obtain one real ChatGPT and one distinct real non-ChatGPT consumer of the **same** approved commit and identical decision revision.
4. Compare with the existing baseline on eligible new tasks: operator handoffs, scientific results/negative retention, qualified development throughput, CPU/memory/latency and failures.
5. Prove a new priority is applied only at the *next eligible planning boundary*, with zero changes to sealed first-use cohorts, in-flight tasks, running controllers, scientific acceptance or KTRADE trading safeguards.
6. If the result is not measurably beneficial or a regression occurs, retain the existing active workflow and rollback **steering only**.

No automatic live steering or consolidation of existing CKB-plane/KTRADE execution authority is authorized by this document.
