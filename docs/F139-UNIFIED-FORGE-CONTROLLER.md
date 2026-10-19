# F139 — One workstation controller; GitHub-hosted execution workers

**Host decision: the user's always-on Windows workstation is the exclusive controller host.** When it is off, research pauses safely. Cloudflare is **not used** to host this controller. Cloudflare D1 may independently support FORGE FSA scientific first-use authority under its own controls; it is not the controller's job queue or scheduling plane. FORGE never connects to CKB-plane.

## Operational ownership

1. A single FORGE Python controller, launched silently by one Windows Task Scheduler startup task, owns the exclusive execution decision. The Windows scheduled task supervises only process start/restart; it does not itself decide which research or optimizer work to run.
2. Local SQLite in FULL synchronous, WAL mode holds source identity, approved task queue, unique active intent, daily budget, immutable evidence chain and run/custody locations. A kernel-level mutex prevents concurrent workstation processes. Intent-before-dispatch and an unreplayable START_RISK state prevent duplicated jobs across Windows restarts or network ambiguities.
3. A fixed GitHub workflow (`forge-f139-development-worker.yml`) is **execution-only**. It has no cron or successor dispatch hooks; it accepts only source-bound, HMAC-authorized development tickets under one owner epoch, uses GitHub-hosted Ubuntu and Windows runners, executes FORGE's existing synthetic model-free advisory, and uploads source-bound receipts.
4. The controller independently authenticates the GitHub event, exact source, attempt, jobs, metadata, artifact ZIP digest and each internal JSON receipt. Raw ZIP members are durably retained on the workstation, not left to 90-day GitHub artifact expiration. Successful results are journaled, then the next approved development task is launched without another GitHub-to-GitHub orchestration hop.
5. Under approved policies, independent Wingless, Yggdrasil and optimizer tasks will eventually use the same controller queue; **F139's initial execution adapter is development-only**, not an original science dispatcher. New science originals, sealed holdouts, owner first-use grants, accepted result promotions and optimizer activation remain separately protected. The controller must never infer approval from green synthetic workflows.

## Current delivery boundary

This PR replaces the earlier draft Cloudflare Worker/D1 controller design with a native workstation controller and local SQLite. It does **not** deploy anything to the workstation, activate scientific execution, change current GitHub schedules, or turn off the existing F136/F137 windows recovery task. Existing GitHub-hosted qualification and Windows Task Scheduler recovery continue until a source-qualified cutover on the actual workstation.

The implementation supports a bounded frozen queue, dynamic next-task selection within that approved queue, successive verified development jobs, per-attempt quarantine, full source identity checks, local signed-by-hash evidence, failure recovery with no blind redispatch and safe startup after power loss. Full independent scientific policy/custody authority is a **future extension**, not claimed here.

## F139-D2J: frozen development succession tranche

The post-D2I controller does not reinitialize its SQLite queue. Instead, the
D2J source defines an **exactly once** source-bound two-ticket tranche, admitted
by the existing controller after the immutable historical record has been
promoted to the qualified new protected main. Admission requires exactly the
two authentic D2C verified historical runs, the two adjudications, and three
append-only source transitions. The third transition is the guarded D2J
production cutover, which brings the event ledger to 14 entries before any
new ticket can be admitted.

When an idle tick sees that frozen state and GitHub protected-main identity
matches local SQLite, the controller commits one
`UNATTENDED_SUCCESSION_ADMITTED` event plus two `TASK_INTAKE` events in one
transaction, then dispatches the first model-free development ticket. It
automatically reconciles both GitHub-hosted Windows and Ubuntu receipts,
moves to the second ticket, and stops after exactly two new developments.
A crashed or ambiguous attempt is not re-dispatched. No second scheduler
or owner is introduced; worker dispatch still uses existing signed HMAC
tickets, source pinning and quotas.

**Boundary:** this is an authenticated, **finite** proof of new-work admission
and consecutive autonomous development executions, *not* an endless work
selector and not a scientific cognition advancement. GitHub workers still
run synthetic model-free advisories. No sealed experimental originals,
first-use authority, optimizer policy promotion, branch modification,
Cloudflare controller, CKB-plane integration or paid inference is authorized.
New classes of work require separately qualified source-bound policies.

Existing F139-D2I production checkout, source-bound 13-event SQLite and
Windows task must not be changed by GitHub PR CI. After protected GitHub
merge, the workstation requires a guarded one-event source transition and
hidden task rebind before any new worker dispatch can pass the SHA check.
Do not silently merge with the old controller running and assume admission
has started: an unmatched main SHA correctly fails closed.

## F139-D2K: bounded discovery of owner-authorized development work

The D2K candidate selector is an explicit trust-boundary extension, not a
free-running synthesis or science experiment. It is **disabled on the deployed
D2J source until a separately qualified protected-main transition and native
Windows acceptance**. D2K discovers open issues already labeled
`f139-development-eligible` on the FORGE repository and admits at most one
source-pinned development issue per idle controller tick. It requires an issue
authored by the repository owner, `author_association=OWNER`, no pull request,
an exact 40-byte protected-main SHA, a schema-typed JSON body, a fixed allowed
lane and `model-free-development-advisory` kind, explicit false scientific
first-use, and zero paid model calls. No free-form issue body is executed.
The immutable GitHub issue number, API issue id, source and canonical body
digest determine one once-only ticket. An edited or relabeled issue cannot
reset its historical issue number for another dispatch. Untrusted sources
fail closed rather than being converted into work.

The SQLite event chain retains the admission's issue id, canonical body SHA,
UTC day, ticket, manifest digest and prior event head. Source checks,
single-owner locks, terminal verification, artifact custody and the existing
start-before-POST replay barrier remain intact. Conservative limits are four
new admissions per UTC day and 80 lifetime total tasks, including history.
The controller examines only qualified issues and idles when none exist; it
does not manufacture synthetic tickets to appear autonomous.

**Substantive limitation:** This initial selector still dispatches the
existing *model-free development advisory* worker, not a task-specific code
change, genuine original scientific experiment, new trained cognitive model,
or independently generated issue. A true useful-work autonomy claim needs a
separately qualified worker adapter that consumes source-bound issue context,
produces a measurable issue-specific engineering outcome and authenticates
that outcome in the receipt. A continuing supply of qualified issues is
also needed. Fully unattended research planning/scientific first-use remains
separate and unauthorized.

## Safeguards

- Default-off and empty queue. No arbitrary scripts, API endpoints, shell commands or new scientific first-use or broker privileges are accepted as queue entries. Before dispatch, both protected `main` SHA and enabled/suspended authority are checked.
- Max 48 once-only development starts per UTC day, single active start-risk in SQLite, one controller mutex, no unqualified or source-drifted task, and no rerunning an ambiguous start.
- Any failed or suspicious result stays retained as `QUARANTINED`. An interrupted GitHub dispatch that may have succeeded stays `START_RISK`, never reissued. Stalls are reported; no silent success.
- SHA-256-linked SQLite events and exact provider receipts are retained locally. **This is local tamper detection, not independent cryptographic signing or proof against a full coordinated disk rollback.** Cross-device backup and FSA independent custody remain important for protected science.
- The currently active GitHub F136/F137 dispatch paths and F137 Windows scheduled task remain untouched. `activate` must verify their deactivation against **live GitHub workflow state** and the **actual Windows Task Scheduler state**, as well as an explicit qualified cutover evidence packet.
- FSA Cloudflare D1 remains available **only for independent scientific authority/custody purposes** and is not altered by this project.

## Qualification and final cutover

1. PR-only native Linux + Windows unit tests must validate real SQLite transactions, source/lineage identity, two-ticket automatic succession, restart/no-replay, timeouts, tampered evidence, adversarial API metadata, per-lane quarantine and Windows Task Scheduler **dry-run**. Full FORGE Linux/Windows Go tests, race, vet and builds remain required.
2. Once merged, verify a fresh exact-source native Windows checkout, Python 3.11+ and GitHub CLI under the actual Windows user; initialize the disabled DB and local evidence path, set one protected GitHub `F139_WORKER_HMAC_KEY` secret and DPAPI-encrypted counterpart. The one-time secret setup cannot be performed from this GitHub-only environment.
3. Install the **inert** Windows logon task and verify process restart without dispatch. Run a disabled shadow acceptance, including a source-pinned two-task development-only manifest and fault injection against a fake provider and real GitHub read-only observation.
4. Perform a separate explicit operational cutover only after all proofs pass: disable the older FORGE F136/F137 GitHub dispatch workflows, ensure no old run is active, disable the existing FORGE F137 Windows task, verify the results live, and activate local F139. Do not disable CKB-plane or touch independent Wingless/Yggdrasil schedulers.
5. Observe **two genuine** consecutive GitHub-hosted worker executions automatically launched from the workstation controller, full immutable custody readback, a simulated interruption, and restart without manual handoff. Only then mark FORGE development orchestration moved. Scientific research first-use autonomy remains gated by independently qualified, authorized FSA and original-trust conditions.

See `f139/README-WINDOWS.md` and `scripts/Install-FORGE-F139.ps1`. Existing `f139/verify_ticket.py` and the fixed worker workflow are retained. No Cloudflare deployment is performed.
