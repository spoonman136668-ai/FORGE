# RSI-R3 EXP-G1 — source grammar growth (development-only preregistration)

**Frozen before implementation or measurement:** protected FORGE source `57ab110cc7dbd5655674fcb9223481f82e70f01c`, tree `eb7363c7973e566dd7bb33f9321ee71781497084`; predecessor source `f139/rsi_r3_source_cycle.py` Git blob `a643c4320654223820ca2666300767465e0cdc3c`.

**Purpose:** Determine whether a bounded, reviewed FORGE *source-program change* expands the original R3 candidate grammar, such that executing the changed developer G1 source actually produces a G2 operator that unchanged G0 could not produce. This is an engineering capacity test, NOT evidence of recursive performance improvement, novel model intelligence, or an unattended original-owner code revision. The G1 source patch is human-authored and cannot count as an autonomous candidate. It must not be scored as a scientific gain.

**One hypothesis:** The original four-program grammar cannot emit a `min(row[2], row[3])` combination. A strictly typed source rewrite of the original generator to add that fifth combinator and its required `min` builtin will allow the separately inspected G1 generator source to execute G0->G1->G2 development feedback and emit a distinct G2 Python program. The unchanged G0 must reject operator 4. The G2 source must calculate the balanced score correctly; this does not imply that the balance rule improves any real FORGE engineering task.

**Fixed test controls and stop rules:**
1. Authenticate the original preimage as a Git blob and demand both exact source anchors; accept no user-defined source, path, shell, or dynamic imports.
2. Only the `RANK_EXPRESSIONS` assignment and the fixed builtin dictionary in `_run_verified_parent` may change in the G1 source; all other original AST nodes must remain identical. G1 must be reproducible from the original bytes.
3. G0 and G1 must receive identical G1-selection feedback. G2 feedback is the fixed synthetic development rows `((3,(12,5,5,4)),(4,(12,3,9,9)))`. Zero randomness. G0 must refuse operator 4 and G1 must deterministically emit and execute the novel G2 program.
4. Retain no authority: all owner, worker, first-use, science, policy, deployment and source-promotion booleans false. No researcher-original data, no paid calls, no new controller, scheduler, workflow, or task.
5. Negative controls: wrong original source Git blob, injected arbitrary Python, malformed grammar, consumed G1 identity, changed output or receipt, and source AST drift. Report every failure; no post-result change to test scenarios to claim PASS.

**Classification:** A passing change proves `ENGINEERING_CAPACITY_DEV_PASS` only. It does not test the already-frozen issue #1550 efficacy requirement of >=1.10x G1 over strongest conventional control plus >=1.10x G2 over G1 on genuinely unseen original engineering work, both Linux and Windows with whole-process costs and full regression. These original criteria remain binding and previously consumed #1539/#1554 cohorts stay excluded. Failures cannot be rehabilitated by moving thresholds.

**Scope and qualification:** Add this prereg, `f139/rsi_r3_source_grammar_growth.py`, and `f139/test_rsi_r3_source_grammar_growth.py` only. Run existing exact-head cross-OS CI, the complete final FORGE regression/build, and protected-main verification before any source-only merge. Do not change the deployed F139 owner or its Wingless/Yggdrasil lanes.
