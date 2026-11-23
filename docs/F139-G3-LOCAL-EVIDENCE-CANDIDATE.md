# F139 G3 — Distinct bounded local evidence candidate (source-only)

The previous G1 `tier-local-partial-pooling-when-unobserved-v1` experiment was
executed and negatively retained. G3 tests a **different mechanism**:
minimum local evidence before choosing an action (three observations per arm).
It does not pool from other contexts and does not introduce memory, oracles,
model calls, new controller/scheduler/queue, or scientific first-use.

Source generator: `f139/nci04_candidate_producer_g3.py`.
Frozen self-tests: `f139/test_nci04_candidate_producer_g3.py`.

This is a candidate *hypothesis*, not an observed learning improvement.
It could degrade exploration by abstaining longer. Strong conventional
fixed-threshold and adaptive-confidence controls, unseen contexts, retention,
and full costs are still required. The source constructor accepts the exact
parent commit, verified original bytes, pre-outcome history digest and
already-consumed mechanism/candidate identities; duplicate inputs fail closed.

Current gate is **source-only qualification**. The module has no GitHub
write endpoint. Do not call G2's existing publisher or live owner until an
independently verified nonconsumed target source and qualified parent are
available. Protected main and original F139 owner must remain untouched.
