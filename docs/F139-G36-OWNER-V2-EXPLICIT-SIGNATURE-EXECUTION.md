# F139 G36 — original-owner V2-only claim and native worker entrypoint

G35 source qualification was 8/8 checks PASS on commit 31322cd.
G36 introduces a separate versioned original owner HMAC domain for a
PRE-DISPATCH claim, bound to the original fresh native admission event and
the subsequent exclusive original START_RISK claim event. The signer reads
and verifies the existing SQLite SHA-chain but does not write it.

A second credentialed authorize-v2 step must check BOTH original V1/native
HMACs and the independent V2 signature before credential-free V2 testing.
The V2 worker checks exact source commit/tree, native candidate identity,
two job outputs, source/ref/event/run attempt and original proof hashes;
then runs the pre-existing G13 V2 fixed original-source regression, writes
a distinct V2 ZIP using G33 and never writes V1 receipt files.

This pre-dispatch signature is NOT the G31 post-run signed permit. It binds
owner event/claim before GitHub allocates a run ID. Final owner receipt
custody must still generate and verify G31's distinct run-bound permit,
use G35 authenticated remote outer artifacts and G32 authentic SQLite
admission before any original terminal write.

G36 source alone CANNOT restore real autonomy: the EXISTING F139 production
controller still invokes V1 fields and must be explicitly guarded-migrated
to call original_owner_v2_fields UNDER its exclusive mutex, use native_protocol
v2 only on new nonconsumed Yggdrasil candidates, and POST once. No new
controller, worker scheduler, queue, background task, paid API or FSA science.
Negative original issue #907 and consumed G1/G3 cannot be replayed.

A PR-only workflow rehearsal must NOT be treated as native-original
execution. Real unseen-source native work requires original-only custody
and unattended natural tick evidence after guarded activation.
