# Public FORGE source qualification — pinned baseline 2026-10-10

## Immutable starting point
- Repository: `spoonman136668-ai/FORGE` (public).
- Baseline commit: `fc50538f7d9151721299ffbb1ccfbb018354c08f`.
- Scope: public FORGE source and its existing `.github/workflows/qualify.yml`.
- This document records the baseline for a public-repository pull-request CI run. It is not a test result or a scientific admission certificate.

## Required source qualification
The existing public GitHub-hosted workflow must independently finish **successfully** on this PR's exact head. Both `ubuntu-latest` and `windows-latest` must execute real steps; queued/failed/no-step jobs do not qualify. Source acceptance requires:
1. `go test -count=1 ./...`
2. `go test -race -count=1 ./...` on Linux
3. `go vet ./...`
4. Native Go build on Linux and Windows, with the existing public-source isolation checks
5. Exact commit, workflow run ID, attempt, job conclusions, and a reproducible output trail

The PR's source tree differs from its baseline only by this documentation file. A CI success validates the public FORGE source at this exact PR commit; it does **not** establish runtime or scientific end-to-end acceptance.

## Explicit non-authority
No FORGE Scientific Authority activation; no unattended scientific progression, experimental admission, primary dispatch, sealed evaluation use, accepted-reference modification, external-source certification, CKB controller change, KTRADE access, or live broker operation. No claims of full end-to-end scientific acceptance until the separate authenticated authority, fault-injection, cross-platform, dual-lane progression, and soak gates pass.

## Context
An earlier FORGE qualification attempt ran from the **private** `ckb-plane` repository and failed before any GitHub-hosted job steps ran. That private-repository failure cannot substitute for qualification in this public repository, and it is not a FORGE code-failure witness. This PR deliberately runs the existing FORGE public workflow instead.
