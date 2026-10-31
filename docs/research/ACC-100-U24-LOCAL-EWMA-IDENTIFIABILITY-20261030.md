# ACC-100 — U24 local-cell mechanism identifiability verdict

Status: **NO_GO_NOVEL_MECHANISM** (algebraic source inspection); **CI PENDING**, **RUNTIME UNVERIFIED**, **SCIENCE NOT GRANTED**.

## Immutable custody
- Input draft PR #1327 head: `09efff236e0b84dbf281f4c05f5641e9aff18adf`.
- Earlier prereg: `docs/research/ACC-94-U24-CHANGING-RULE-PREREG-20261030.md` (unchanged).
- Local candidate: `research/acc95_u24/local_cells.py`.
- Conventional comparator: `research/acc95_u24/ewma.py`.
- Existing Linux/Windows run at input head: #2654, ID `41154152476`, **pending at inspection**. Do not substitute workflow existence for PASS.

## Algebraic falsification
For neighborhood i and update target y in {0,1}, local cell L:
`L_i' = (1-alpha) L_i + alpha (2y-1)`, initialized `L_i=0`.
EWMA cell M:
`M_i' = (1-alpha) M_i + alpha y`, initialized `M_i=0.5`.
Define `L_i = 2 M_i - 1`. Then:
`2 M_i' - 1 = (1-alpha)(2 M_i - 1) + alpha(2y-1) = L_i'`.
Predictions are `L_i > 0` and `M_i > 0.5`, respectively. Thus at mathematical exact precision, both produce identical predictions after any identical sequence of allowed observations, for each frozen rate, including after a rule switch. Floating-point implementations may have roundoff/tie differences; those do not establish a distinct learning mechanism. Eight local cells versus eight EWMA entries is a renaming/reparameterization, not scientific novelty.
No query labels are available to update() in either candidate. Their count arrays are ancillary diagnostics, not different update dynamics.

## Fail-closed decision
- Reject a claim that the current ACC-99 local candidate beats matched EWMA as an independent learning method. **NO_GO_NOVEL_MECHANISM** without needing to consume reserved TEST or original-world first use.
- Do not compute a scientific speedup, quality gain, or cross-platform PASS from this proof.
- Run/qualify already committed regression tests when eligible, but do not promote or merge to native model as an advance.
- Continue research only with a **genuinely non-affine, preregistered change** (e.g. multiple interacting local cells with constrained message-passing and lesion/communication ablations), compared with matched filtered tabular and recurrent controls. That requires its own prospective frozen mechanism/source identity, FIT/DEV instrumented proof, and separately authorized held-out test.
- Existing ACC-94 thresholds and protected TEST seeds/rules remain unchanged; no tuning against TEST, no controller or runner modification, no acceptance authority inferred.

Plain English: The local candidate and EWMA make the same mathematical predictions because one stores twice the other's state minus one. This explains why a seemingly new learner cannot yet count as scientific progress.
