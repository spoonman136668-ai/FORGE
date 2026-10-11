# FORGE Dream-RSI R8 — GitHub-hosted compute with independent FSA control

Status: bounded source-only compute demonstration, NOT FSA activation or scientific original execution.

## Architectural decision

GitHub-hosted Linux and Windows runners are the default proposed compute substrate for independent Wingless and Yggdrasil experiments, subject to source identity, FSA authorization, quotas and workload fit. Dedicated always-on science machines are not intrinsically needed. However, ephemeral hosted VMs, public Actions workflows and temporary artifacts are NOT a durable first-use ledger or independently controlled FSA signing authority.

This change deliberately has no FSA signing keys, OIDC grants, runtime secrets, paid cloud resources, scheduler, accepted-ref writer, original experimental cohort, or science dispatch. It only proves the complete isolated hosted compute workflow with deterministic NONSCIENTIFIC fixtures.

## Immutable source and change scope

The parent is exact qualified FORGE R7 commit 2a7745660edab26319b8eb6396e2c5dd406ff8db. R8 adds exactly five paths:

- hostedcompute/shadow.go: independently verified Git SHA and tree SHA, immutable run and first-attempt identity, frozen four-job manifest and recomputable receipts
- hostedcompute/shadow_test.go: lane/OS, changed source, replay attempt, budget cap, forged digest, missing or duplicate artifacts and forbidden authority bits
- cmd/forge-hosted-shadow/main.go: exclusive-create prepare, work and independent-reconcile CLI, without network calls
- .github/workflows/qualify-dreamrsi-r8-hosted.yml: native hosted Linux and Windows qualification, followed by two Wingless jobs, two Yggdrasil jobs and separate reconciliation
- This report

The workflow triggers only from the designated proposal branch's first push attempt. Source qualification gates all shadow work. Standard hosted Linux and Windows workers have repository contents READ permissions and no write, id-token, scientific custody, privileged environment or access to CKB-plane/KTRADE. Branch-push source execution is not a live experiment dispatch authority.

## What is actually demonstrated

An Ubuntu prepare job creates a content-addressed NONSCIENTIFIC manifest bound to the exact immutable workflow commit, tree, GitHub Actions run ID, attempt number and four independent lane/OS workloads. Each workload performs exactly 4,096 deterministic SHA-256 iterations. Four separate hosted jobs consume the same frozen manifest and produce separate short-lived source-checked receipts: Wingless/Linux, Wingless/Windows, Yggdrasil/Linux and Yggdrasil/Windows.

A separate fifth hosted job downloads the four receipts and frozen manifest and recomputes every output. It rejects altered source, wrong run/attempt, other lane or OS, altered work units, forged digest, duplicate worker receipt and missing results. Linux and Windows qualification each run focused tests, one full FORGE Go regression, vet and build. Linux runs race tests. This proves reproducible, isolated public hosted compute and reconciliation of **synthetic** work only.

All receipt and reconciliation flags for scientific original, acceptance, dispatch, protected FSA independence and permanent custody are FALSE. The manifest and receipts are stored as GitHub Actions artifacts with a **seven-day retention configuration**. That is only transient transport, NOT immutable archival custody, accepted science, actual experiment-cost savings or original cohort consumption.

## Planned real-science handoff (not enabled)

Frozen Dream-RSI candidate and policy lineage -> independently qualified FORGE FSA preregistration, source qualification and cohort exclusions -> independently durable FSA first-use STARTED/CAS -> strictly bounded, source-pinned *FSA-authorized* compute capability -> separate GitHub-hosted Wingless/Yggdrasil job with no FSA signing or CAS rights -> immutable raw evidence delivered to independently controlled custody -> scientific FSA classification including all negatives and invalids -> next bounded optimization generation.

A hosted science job may not issue the authorization that allows itself to run. The FSA must independently recheck and consume first use *before* handing a task to an ephemeral runner and must retain authenticated raw outcome evidence across runner deletion, reruns and partial failures. In a public repo, do not send sealed or private original science through fork-triggered code, default public logs or temporary shared artifacts.

Separate FSA signing identity, protected monotonic first-use floor and physical witness durability remain unqualified under issue #20. Protected GitHub environments or OIDC can help authenticate a future restricted FSA client, but they are not themselves proof of independent physical custody; neither is provisioned here. This work removes a proposed perpetual research-machine requirement without bypassing scientific authority.

## Qualification commands

go test -count=1 ./hostedcompute ./cmd/forge-hosted-shadow

go test -count=1 ./...

go vet ./...

go build ./...

go test -race -count=1 ./hostedcompute ./cmd/forge-hosted-shadow

R8 passes its stated compute milestone only when the actual GitHub-hosted workflow, not just local unit tests, shows successful Linux and Windows source qualification, all four isolated hosted jobs, independent four-receipt reconciliation and retained SHA-addressed evidence. Anything short is a partial qualification, and no real science or FSA activation may be inferred.

Next gate: independently qualified, operator-authorized FSA custody for real one-shot scientific starts and end-to-end outcome retention. R1–R8 remain stacked, source-only proposals until final acceptance and actual independent authority exists.
