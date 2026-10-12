# Existing-lane operational watchdog R1

Pure read-only shadow watchdog for the original Wingless and Yggdrasil lanes. Requires authenticated observations, nonzero owner epoch and exact journal hash. At greater than 300 seconds since *orchestration* progression it emits DIAGNOSE_RECOVERABLE_STALL; this does not start science or imply an automatic repair has occurred.

Scientific execution has no 300-second runtime ceiling. Missing/aged independently authenticated worker heartbeat produces RECONCILE_WORKER_WITHOUT_REPLAY. Quarantined or first-use-risk work ALWAYS produces RECONCILE_ORIGINAL_NO_REPLAY. An unauthenticated or temporally inconsistent observation fails closed; duplicate or missing lanes are rejected.

Pending infrastructure: authenticated observation producer, durable independent authority, worker supervision, automated bounded recovery actions, and native end-to-end scientific acceptance. This package cannot assert genuine autonomous cycles or supersede CKB authority.
