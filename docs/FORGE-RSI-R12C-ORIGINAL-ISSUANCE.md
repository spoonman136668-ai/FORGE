# RSI R12-C — immutable original reservation and lifetime-one issuance

Parent protected FORGE main: `aa3dbc296a3a30bf9dedcc7c9320db98c6cbfd24`,
tree `2cfe3439f2fc20e926eaa9e5614cea4eb3333193`.

**Bug repaired:** R12-A previously included the mutable current SQLite head in
its original reservation digest. Once an issuance event was appended, cold
revalidation of the identical candidate would have a new binding SHA256. It
now uses the reservation event's immutable `seq`/`sha` snapshot. The full
current head is still checked for concurrent movement during every read.

**R12-C code:** a cold verifier validates at most one issuance across all
source transitions, the historical original R11 reservation, exact R12-B
job intent, candidate digest, owner-source epoch, SHA-chained prior head,
signature digest, retry=false, and all no-execution/no-first-use flags.
A future installed original Windows owner may only write this event under
its existing kernel mutex, provider release-continuity verification, live
enabled state, no active research task, original key custody, exact new
GitHub workflow/job/source identities, and SQLite transaction. A
deliberately distinct `rsi-self-qualification (OS)` job is required;
**the current credential-bearing `execute` worker does not qualify**.

**Inert until separate worker activation:** No controller tick invokes this
function, no current workflow has the required credential-free job, no
signed job or key is returned, no secret is printed, and no original
installation is changed. A green CI test is not an original Windows owner
reservation/issuance and never proves unattended RSI or science.
One-use issuance is source implemented; real live execution, authenticated
worker delivery, negative terminal and result receipts remain separately
unverified, not silently allowed.

Regression: complete existing Linux/Windows FORGE qualification on exact
candidate SHA including tests for immutable binding, event tampering,
forged owner, duplicate original attempts, and worker-lane isolation.
No new scheduled tasks, controller, queue, science first-use or paid API.
