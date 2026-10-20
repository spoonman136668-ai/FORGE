# FORGE - Autonomous Scientific Research Platform

**Status: public source-only prototype. Not deployed or qualified for live scientific execution.**

FORGE develops and evaluates frozen scientific portfolios with deterministic state,
versioned quarantine-only proposal contracts, and content-addressed journal replay.
It models Wingless and Yggdrasil as independent research lanes, aimed at two distinct native **non-transformer, non-token-centric cognitive architectures** with persistent learning, memory and reasoning, eventually targeting LLM-class general capability. Conventional models remain comparators or research tools, never the target cognitive foundation. See [standing research directions](AGENTS.md) and [scientific information-per-compute policy](docs/FORGE-INFO-PER-COMPUTE-NORTH-STAR.md). Its planned
scientific decision-making authority is **FORGE Scientific Authority (FSA)**,
not CKB-plane. FORGE will own its research controller, isolated queue, runner
leases, admission and scientific progression after separate qualification.
The current public prototype is still non-executing and does not yet
implement or activate FSA.

**Hard operator boundary: FORGE must not connect to or depend on CKB-plane.**
Mind-Palace is the **only cross-project context bridge**: bounded, commit-pinned,
**read-only** advisory retrieval directly from Mind-Palace. Do not make FORGE
owner/witness evidence, first-use, optimizers, CI, recovery, or deployments
depend on private CKB-plane repositories, workflows, tokens, controllers,
ledgers, or artifacts. FORGE must qualify these functions natively under its
own safeguards and existing authorized infrastructure, without interfering
with the independent research loops.

See [ADR 0002 (standing separation)](docs/ADR-0002-MIND-PALACE-ONLY-NO-CKB-DEPENDENCY.md),
[agent instructions](AGENTS.md) and
[ADR 0001 (historical design)](docs/ADR-0001-FORGE-SCIENTIFIC-AUTHORITY.md).

## Build and test

Go 1.23 or newer:

```sh
go test -count=1 ./...
go test -race -count=1 ./...
go vet ./...
go build ./...
```

Offline tools: `go run ./cmd/forge-plan -h` and `go run ./cmd/replay -h`.

GitHub-hosted Ubuntu and Windows CI runs on pushes and pull requests.
No private scientific evidence, external-source archives, private backend
controller, broker connection, credentials or sealed evaluation data are
included in this repository. See PUBLIC_SOURCE_BOUNDARY.md.

**Licensing:** no general reuse license has yet been granted. Public visibility
does not automatically authorize redistribution.