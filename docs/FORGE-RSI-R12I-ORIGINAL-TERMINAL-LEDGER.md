# R12-I — one-use post-dispatch original SQLite terminal custody (inactive)

**Baseline** FORGE main `1be35e3715a6d5df0b16b2382654e7984f1afcd4`
(tree `047263aef5ef1e419c34de1f1ff5ab62dffef682`).
Current original-owner release `42c70d74dd93ef90d0f4618fefefe2206b81eafe`.
Original policy issue #807 authorizes ONLY Wingless/Yggdrasil.

## Actual change

R12-I adds one `RSI_SELF_ORIGINAL_TERMINAL` kind to the ORIGINAL
Windows owner SQLite event chain; there is no new ledger/controller.
A future, separately qualified original owner (not an arbitrary
GitHub-hosted runner) can observe the completed provider run and job
via GET, bind their IDs, result, attempt, workflow, repo, source SHA,
ticket and OS to the original R11 reservation and R12-G preissue,
and atomically append a one-shot SHA-chain event. The event is cold
audited by the existing `Database.verify()` even after restart.
A duplicate terminal, legacy issuance collision, synthetic original,
source drift, provider spoof, retry or status mismatch fails closed.
Negative outcomes are stored; neither conclusion permits an automatic
retry. Zero original Windows runtime calls are made by this PR.

The payload records BOTH overall run and individual job conclusions;
the original preissue event, source tree, candidate bytes digest,
reserved failure and original ledger predecessor are frozen. Historical
source transitions are checked. The data-only test exercises negative
cases and a synthetic disposable ledger forgery; it does not fabricate
a genuine original owner run.

## Independent authentication is **still missing**

The shared `F139_WORKER_HMAC_KEY` exists in GitHub's credentialed job.
A SHA-chain event created by an original-only routine does not
independently prove to GitHub that it was written by the original
Windows owner. R12-I therefore **does NOT** sign with that shared key
or advertise a transferable admission receipt. Every
`original_only_public_signature_verified`,
`credential_free_worker_admitted`, `scientific_first_use`,
`source_promoted` and `autonomous_rsi_proven` flag stays FALSE.

Before any live worker admission, original-only asymmetric signing key
custody and a separately pinned/publicly verifiable original-owner
certificate must be established and independently qualified. No key
material, enrollment, rotated trust anchor or signer is created by
this change. An authorized G145-compliant workflow release, installed
original-owner source transition and matching three-lane policy are
separate actual deployment gates. The existing
`.github/workflows/forge-f139-development-worker.yml` is untouched
to preserve concurrent Hybrid and normal research operations.

No scheduled tasks, paid APIs, new runner, queue, controller,
live dispatch, original event mutation, policy change, first-use,
owner release or source promotion occurs here.
