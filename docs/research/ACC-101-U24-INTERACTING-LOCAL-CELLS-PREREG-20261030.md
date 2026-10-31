# ACC-101 — Non-affine local communication candidate: prospective source-only freeze

Status: **PREEXEC_FREEZE / NOT IMPLEMENTED / NOT RUN / NO SCIENTIFIC ADMISSION**.
Parent is ACC-100 no-go at immutable commit `4c2fd4c42ed8b6c211d7c0da0b090d9001153a53`. Existing PR #1327 remains draft. ACC-94 reserved TEST cohort remains sealed. GPU ACC and native Yggdrasil/Wingless are independent and untouched.

## Rationale and falsifier
ACC-99 `LocalCells` is exactly an affine reparameterization of eight-entry EWMA, so it is **not** evidence of a new mechanism. This proposal must add **nontrivial interactions** between cells while preserving local observations. It cannot treat more parameters, shared target labels or direct rule-switch timing as an advantage.

H0: information-matched local message passing does not surpass the best frozen conventional adaptive counting, EWMA and recurrent controls on post-switch accuracy/adaptation error under equal total cost.
H1: bounded neighboring-cell communication and a persistent two-timescale state yield measurable post-switch improvement at acceptable CPU, RSS, state and communication cost.
H2: any performance gain is explained by extra bits, tuning or leaked labels; a matched-capacity, identical-information comparator removes it.

## Candidate mechanism frozen before outcome
Eight cells indexed by the three-bit neighborhood pattern `0..7`. Cell i receives only its own visible (neighborhood,label) pairs, its persisted fast/slow states and messages from two neighboring cells in the **fixed 3-bit Hamming cube**, chosen by flipping the least and most significant bit. Messages must be derived from **prior-step local states**, never current evaluation labels or global rule identity. A cell emits a quantized signed 8-bit prediction/confidence pair once per step to each neighbor; count payload bytes, per-edge routing bytes and serialization. All messages are delivered one step later synchronously, not recursively in the same step. No all-to-all communication or shared global gradient.
Local fit update: maintain two EMA traces with `alpha_fast=0.3`, `alpha_slow=0.02` and a bounded error flag `e_i=clip(fast_i-slow_i,-1,1)`. Candidate output score at time t is `fast_i + beta*tanh(sum_{j in N(i)} e_j(t-1) / 2)` with frozen `beta=0.25`. The neighbors' error flags are transmitted using signed int8 nearest-neighbor quantization, saturating endpoints. Predictor uses score >0.5. Future labels NEVER reach other cells; messages are derived from historical local fit only. Rates, topology, quantization and beta are fixed before measurement.
All eight cells use identical update code, but **separate persistent state**; no pretrained model, oracle or external data source. Record all update and message operations.

## Ablations and fair controls
A: candidate with two-neighbor delayed messages.
B: same candidate with communication disabled (messages zero) and otherwise identical fast/slow state; controls extra state.
C: shuffled sender endpoints fixed per episode from FIT-only seed; equal communication budget; tests whether actual local topology matters.
D: strongest ACC-98 non-oracle EWMA rate selected on FIT/DEV only (0.02,0.1,0.3,0.7); carry-over ACC-97 table; the existing oracle reset remains visibly unfair upper bound.
E: matched-capacity per-neighborhood fast/slow EMA with no message passing, and conventional recurrent control with equal observations. If the latter is unimplemented, report CONTROL_INCOMPLETE and never accept superiority.
Every arm sees exactly the same visible transitions in the same order; phase query truth is evaluator-only. All arms process 128 pre-switch, 64 adaptation and 128 post-switch steps on the **existing** frozen FIT/DEV rule and seed sets, with 25% of cells exposed per time step. Preserve existing 25/63/127 lattice-width constraints, immutable trace hashes and exact cold-restart requirement. No TEST samples, no TEST rule identity use beyond documented sealed identifiers, no native model source ingestion.

## Measurements, rejection and custody
Keep ACC-94 conjunctive DEV screen: >=+0.05 mean post-switch prediction accuracy over strongest fair baseline, >=10% less cumulative adaptation error, no rule worse by >0.02, exact cold restart, <=1.10x aggregate CPU/RSS/state+communication. Count routing, encoding, decoding, copies, and full worker CPU. Test prediction parity between in-memory continuation and independent restore, verify no evaluator-query access, ensure messages are computed before next-step visible labels, verify deterministic digests and full split isolation.
Negative gates: if candidate with messages disabled is equivalent or stronger, conclude COMMUNICATION_NOT_HELPFUL; if shuffled topology is equivalent, conclude TOPOLOGY_UNSUPPORTED; if matched conventional arm wins, NO_GO; if resources are missing, RESOURCE_UNVERIFIED. Do not use a runtime success as scientific acceptance.
All developer tuning is FIT/DEV only. Hold out the reserved TEST exactly as preregistered and keep the mandatory full Linux/Windows regression and independent science authorization separate.

## Execution order
1. Verify exact source head/clean provenance and current CI at implementation time. No assumption that queued CI passed.
2. Implement deterministic, no-side-effect source-free candidate plus ablations and failing negative tests on the **existing draft PR**, no new controller.
3. Offline focused tests and bounded FIT/DEV screen; log counters and immutable receipts. Unverified resources or scientific controls block claims.
4. After focused qualification, separately run required final full regression. No merge/first-use/promotion absent verified contract and authority.

Interpretation: a genuinely different communication path can be falsified cheaply without pretending an equivalent EMA state is novel. **This prereg alone proves no learning improvement.**
