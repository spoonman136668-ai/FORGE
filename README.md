# FORGE â€” Autonomous Scientific Research Platform

**Status: public source-only prototype. Not deployed or qualified for live scientific execution.**

FORGE develops and evaluates frozen scientific portfolios with deterministic state,
versioned quarantine-only proposal contracts, and content-addressed journal replay.
It models Wingless and Yggdrasil as independent research lanes. CKB-plane can
serve as an external independently governed execution/qualification backend;
FORGE itself has no execution, admission, or scheduling authority.

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