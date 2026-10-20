# FORGE F139 native Windows controller (no Cloudflare hosting)

The Windows workstation is the **only** scheduler/dispatcher. `f139/local_controller.py` uses Python standard library SQLite to preserve write-before-dispatch intent and SHA-256-linked local events, queries GitHub Actions via the **existing authenticated `gh` CLI**, and starts only `forge-f139-development-worker.yml`. Neither GitHub nor Cloudflare chooses tasks. The worker runs a bounded synthetic advisory and retains receipts from Ubuntu and Windows. Cloudflare D1 may still be used independently for **FSA scientific custody**, never to host/drive this controller.

## First use, only after review and source qualification

1. Install Python 3.11+ and GitHub CLI `gh` on the workstation if not already present; log into GitHub as the authorized FORGE account and verify `gh auth status` against `spoonman136668-ai/FORGE`.
2. From the qualified F139 checkout, initialize the database explicitly: `python -B -m f139.local_controller --db "$env:LOCALAPPDATA\FORGE-F139\state.sqlite" init --source-sha <EXACT_QUALIFIED_MAIN_SHA>`. Initial state is `enabled=0` and queue empty. It does not dispatch.
3. Qualify one bounded *development-only* task manifest with schema `forge.f139.development-queue.v1`, containing only `ticket`, `lane` (Wingless/Yggdrasil/Qualification), and frozen `source_sha`. Queue it using the `queue --manifest <path>` CLI **while disabled**. This is not new scientific first-use authority. No arbitrary executable commands or working directories are accepted.
4. Generate one high-entropy random HMAC key, configure it once as the GitHub repository secret `F139_WORKER_HMAC_KEY`, and run `scripts/Install-FORGE-F139.ps1 -ConfigureKey` as the same Windows account that will run the controller. It persists only a Windows DPAPI-encrypted current-user copy. Never commit, chat, or log the secret. Keep GitHub `gh` authentication under the same Windows profile.
5. Run `scripts/Install-FORGE-F139.ps1` with no switches for a **dry-run**. The optional `-Apply` installs a hidden, logged-on-user Task Scheduler process; it does not activate the controller or disable existing F136/F137 tasks. Verify automatic startup and log creation. A workstation powered off simply pauses FORGE; startup at logon resumes reconciliation, never a blind retry.
6. Only after **native Windows real GitHub-hosted worker acceptance** and independent evidence of disabling **both** FORGE GitHub legacy dispatch workflows and the **FORGE F137 Windows scheduled recovery task**, create a qualified `forge.f139.local-cutover-evidence.v1` attestation and run the CLI `activate --legacy-suspended-evidence <path>`. The controller will then begin assigning from its frozen development-only queue. Never activate F139 alongside the legacy dispatch owners. Do not touch the independent CKB-plane controller.

## Development-first use (operator decision 2026-10-20)

The F139 controller and its fixed worker are **development-only**. Routine
private Wingless/Yggdrasil mechanism implementation, development-seed training,
regression diagnosis and ablations **do not require FSA's independent witness**.
The existing FSA first-use requirements apply only when an operation would
consume protected scientific originals, access sealed holdouts, or make an
independently accepted scientific claim. Those operations remain prohibited here.

**Current capability limit:** the F139 normal worker invokes
`forge-model-free-loop --synthetic-only`; D2K tickets run allowlisted FORGE
Go-package diagnostics. Neither is a trained-cognition developer, produces
Wingless/Yggdrasil implementation diffs, nor advances a learned mechanism by
itself. Do not describe a successful synthetic job as autonomous science.

Next eligible engineering work: attach an explicitly development-only,
source-bound **real mechanism code/training/test adapter** to the existing F139
queue, with independently verified source/diff and negative-result receipts;
perform qualification before enabling that adapter. Keep the existing source,
epoch, one-shot start-risk and no-retry controls. Never enable the existing
scientific worker path via this development decision. No separate scheduler,
new infrastructure, API bill, or witness-provisioning task is authorized.

See `docs/F139-DEVELOPMENT-FIRST-DECISION.md`.

## Guarantees and limitations

- A logged-on Windows user and running workstation are required for this Task Scheduler startup strategy. No machine-off research continuity or Windows startup *before login* is claimed.
- A crash, POST timeout, missed HTTP acknowledgment, or absent GitHub run leaves the ticket in `START_RISK`; it is **never automatically re-dispatched**. Independent review must resolve the original start risk. Other preapproved ready tasks cannot silently mask an indeterminate run.
- GitHub run/job/artifact identity and ZIP/receipt SHA-256 are checked before a task enters `VERIFIED`. The full ZIP members and append-only local SHA-256 evidence are retained. Local hash chaining is **not** a separate external witness against a full coordinated disk rollback. Backups and independent custody are still required for production scientific first-use, and external FSA D1 is not a blanket permission.
- Nonterminal failures are quarantined, not discarded; other qualified development tasks can advance on the next tick. Signed scientific original grants, independent owner/witness admission, optimizer promotion, paid model calls, and protected `main` writes are not implemented or allowed.
- Changing `main` source identity stops new work until a separately qualified source transition occurs. No silent upgrade of frozen studies.

## Regression

`python -B -m unittest discover -s f139 -p 'test_*.py' -v` on native Windows, plus the existing full FORGE `go test -count=1 ./...`, `go vet ./...`, and `go build ./...`. The F139 source CI runs on both Windows and Linux without installing the controller or provisioning any credentials.
