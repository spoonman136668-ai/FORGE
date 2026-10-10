# Observed CKB research-loop changes — FORGE compatibility register

This public register records only **high-level interface changes** checked
during FORGE work. Detailed authenticated controller, runner, experiment and
source evidence remains in the private CKB authority domain; this register
is **not runtime telemetry, scientific acceptance or a FORGE authorization**.

| Date | Latest checked CKB main | Observed change | FORGE action |
|---|---|---|---|
| 2026-10-10 earlier | R216 S17 | S09 frozen once-only admission preflight; no S09 primary executed at this original baseline | Preserve one-shot, frozen controls, independence |
| 2026-10-10 later | R216 S22 | CKB-only S09 first-use entry activated after separately qualified S18-S22 source, authority and non-replayable ledger gates | Record upstream improvement; do **not** import CKB scheduling/authority into FORGE |

**Important:** S22 merging or workflow activation does NOT establish that
the independent S09 experiment has finished, that a result is scientifically
accepted, or that FORGE may reuse any original cohort. Verify original
run/terminal/acceptance evidence privately before making those claims.

**Carry-forward engineering patterns (not controller sharing):**
write-once cohort consumption, first-use receipts, independent scientific
qualification and provenance validation. FORGE separately qualifies all
analogous implementations as native FSA components. Existing CKB and KTRADE
controllers, queues, runner leases, accepted refs and execution permissions
are strictly outside FORGE's domain.

**Routine:** On relevant FORGE milestones, compare the newest CKB main to the
last observed stage; record only actually verified changes and any required
FORGE compatibility/qualification delta. Do not claim continuous between-chat
monitoring or mutate CKB while observing.
