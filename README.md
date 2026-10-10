# FORGE - Autonomous Scientific Research Platform

**Status: public source-only prototype. Not deployed or qualified for live scientific execution.**

FORGE develops and evaluates frozen scientific portfolios with deterministic state,
versioned quarantine-only proposal contracts, and content-addressed journal replay.
It models Wingless and Yggdrasil as independent research lanes. Its planned
scientific decision-making authority is **FORGE Scientific Authority (FSA)**,
not CKB-plane. FORGE will own its research controller, isolated queue, runner
leases, admission and scientific progression after separate qualification.
The current public prototype is still non-executing and does not yet
implement or activate FSA.

Mind-Palace will supply bounded, pinned, **read-only** advisory context directly,
without requiring the CKB controller or publishing private context.
CKB-plane is an optional historical evidence source, not FORGE's authority.
See [ADR 0001](docs/ADR-0001-FORGE-SCIENTIFIC-AUTHORITY.md).

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