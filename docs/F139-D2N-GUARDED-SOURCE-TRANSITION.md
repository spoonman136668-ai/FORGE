# F139-D2N — Guarded protected-main source-only transition

## Frozen predecessor and accepted historical evidence

- Existing Windows F139 controller source: `4a5665d9d01b6e68effc00be244ac39b6794a222`
- Accepted historical prefix length: exactly 23 events
- Historical event 23 SHA-256: `eea95c859f9a59f700612c3b7b39152abc78827981976e9d86567c29fa03ff87`
- Historical tasks: exactly four `VERIFIED` records
- Archived evidence: exactly eight GitHub provider-digest-matched ZIPs
- Original first-use scientific authorization: **false**

The operator's native Windows read-only D2M run reported all of those checks
PASS. This is a local receipt, NOT independently signed external FSA custody.

## Source-only compatibility repair

Protected FORGE `main` had advanced to
`df97a80b00f22c401534470b6470dd4ff29c3597` when this candidate was
frozen. Merging this patch changes `main` again; pre-embedding its new commit
SHA in the same patch is impossible. Do not repeatedly grow a static allowlist
by hoping it matches a future merge.

The D2N verifier therefore accepts **at most one final additional**
`SOURCE_TRANSITION_ADMITTED` event beyond the eight already pinned
development-only source successors, under these restrictions:

1. The optional final target is the **exact live GitHub protected-main commit**,
   read independently under the authenticated owner GitHub CLI. A caller-supplied
   SHA by itself is not sufficient for the native Windows CLI.
2. Its source predecessor must equal the immediately preceding journal source;
   every event sequence number, canonical payload, and prior hash must match.
3. The original event-23 SHA remains independently supplied and checked, even
   if a newer source-only head exists.
4. There must still be exactly four originally verified tasks, two source-bound
   D2J admission bindings, and all eight original provider-bound ZIPs.
5. Every source-only suffix must record `new_dispatches=0`,
   `scientific_first_use=false`, and four verified historical tasks.
6. The live-main target must be **the last** suffix; no subsequent event or
   second dynamic target is admitted by this bounded compatibility repair.

Without the optional argument, the previous eight-entry static allowlist and
historical verifier semantics remain unchanged.

## Qualified source-only sequence

- Pin the predecessor and current protected-main identity separately. Check
  source ancestry, branch protection, final CI, and live actual Windows state.
  `GitHub().protected_main()` authenticates branch identity/protection, **not**
  CI completion or an independent scientific signature.
- Run focused verifier negatives plus one complete Linux/Windows regression
  on the exact candidate head. Protected-branch merge and fresh qualified
  Windows task/source binding are separate decisions.
- Before any live source transition, verify sole controller ownership and that
  no task is READY, active, in START_RISK, or uncertain. Preserve all originals.
  Never rewrite existing event records or task rows.
- Only the already qualified sole owner may append one atomic source-only
  transition through the existing `Database.transition_source` contract.
  **This patch does not invoke it, add a CLI write verb, install a task, or
  authorize a host mutation.**
- After the separately authorized append, run the native Windows read-only
  custody verifier with a fresh owner-authenticated protected-main target:

```powershell
python -B -m f139.audit_d2k_custody `
  --db "$env:LOCALAPPDATA\FORGE-F139\state.sqlite" `
  --expected-source-sha "<EXACT_LIVE_PROTECTED_MAIN_SHA>" `
  --sealed-event-head-sha256 "eea95c859f9a59f700612c3b7b39152abc78827981976e9d86567c29fa03ff87" `
  --qualified-protected-main-sha "<EXACT_LIVE_PROTECTED_MAIN_SHA>"
```

Acceptance requires `live_main_source_suffix_verified=true`, four tasks,
eight archives, no original database writes, no controller actions, and no
scientific first-use. A 23-event pretransition audit will return
`live_main_source_suffix_verified=false` even when the live-main SHA matches.

**STOP** on protected-main drift, missing independent historical seal,
post-23 non-source events, multiple dynamic transitions, a failed native
Windows audit, active/unverified tasks, or unsupported owner/source identity.

No FORGE scientific experiment, Cloudflare D1 mutation, CKB-plane alteration,
production rollout, new local runner, competing controller, scheduler or paid
API is authorized by this source-only verifier.
