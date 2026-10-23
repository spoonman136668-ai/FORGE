# O16 — External POPGym learned write/evict (PUBLIC prospective development)

**FIRST-ONLY SOURCE CONTRACT.** Exact source parent: O15 FORGE head `b07e8d5293f12466263986e1f8b9a8b679334e48`. Freeze this protocol BEFORE first O16 original-source execution. Preserve O14 negative, O15 original evidence, F139/Q21/FSA custody, NCI/ITD/BIO/ELG and all protected refs. This is no authority activation, scientific admission, architecture promotion or protected merge.

## Real source and information custody

Pin independently authored `proroklab/popgym@410d5aa626dae8024f498354d8781a0d1870c399`; reuse O15 original-source Git-blob checks for `repeat_previous.py`, `deck.py` and `env.py`. Unmodified real `RepeatPrevious(num_decks=1,k=4 or 8)`, original `reset(seed)` and 51 genuine `step(legal_action)` calls. No policy may inspect source-private deck, true target, `get_state`, returned private `info`, RNG, future observations/queries, or source-law k supplied as input. All learners see only original public suits, legal own actions, original earlier returned rewards, and time; rewards are initially zero, then original signed ±1/(52−k).

**Exception clearly costed:** a shared O15-style lag learner may use full public FIT history to estimate lag 1..12 identically for every arm. Thus O16 does NOT demonstrate fully end-to-end four-record memory; inherited history and training overhead must be reported. Policy DEV data is strictly limited to its **four** records `(timestamp, public suit)`, public current suit, time, and fitted lag/checkpoint. Source k only appears in source constructor and independent auditor.

## Frozen roles and budgets

Conditions `k4,k8`; replicas `0,1,2`. Each condition/rep:
- **LAG_FIT:** 48 original public O15-style shared observations/rewards from seeds `8100000+400000*conditionIndex+10000*rep+i`, i0..47; O15 already publicly exposed these role seeds.
- **POLICY_FIT:** 48 original source episodes for learned writer, seeds `9100000+400000*conditionIndex+10000*rep+i`; same 48 seeds used for properly trained conventional stride selector, with prospectively partitioned 16 episodes each for periods 1,2,4. Each uses its OWN genuinely executed actions and original returned reward, not synthetic counterfactual or privileged targets.
- **DEV:** 24 genuine original source episodes for EACH of FOUR arms, seeds `9900000+400000*conditionIndex+10000*rep+i`, i0..23; original public observations paired across arms, distinct actually executed actions/rewards. Frozen FIT models; zero DEV updates, retuning, resampling or adaptive winner selection.

Total **1440 original source resets** = six scenarios × (48+48+48+24×4); total **73,440 original legal actions**. Validate disjoint role seeds, exactly 52−k scored decisions/episode, original rewards, original episode termination, no capacity violation.

## Frozen four candidates

1. `LEARNED_EVICTION`: six-weight softmax over SKIP and evict one existing record, using ONLY time parity, current record ages and shared learned lag; stochastic exploration only in FIT. Train with delayed original source reward from `step(t+learned_lag)` to credit writer action at t; fixed LR=0.012, weights clipped ±6; fitted parameters immutable in DEV. This is bounded delayed-credit learning, not general-purpose native cognition or a claim of superiority.
2. `FIFO`: write every public suit, replace oldest when full; equal four-record memory.
3. `RESERVOIR`: conventional seeded reservoir with the same record cap and legal information.
4. `TRAINED_STRIDE`: period-1/2/4 writing with oldest replacement, selected only from prospectively split genuine source FIT rewards. This trained conventional comparator receives the same 48 policy FIT episode budget.

Shared readout returns suit at exactly `t−learned_lag` from its own four records, else current public suit; all policy writes happen AFTER original `env.step` with only the already-observed current suit and past original reward. Count FIT source calls, model training/inference CPU, memory state plus timestamps, checkpoint bytes, observation/action/reward SHA, wall/RSS/peak heap if available; energy = NOT_MEASURED.

## Falsification and disposition

For **every replica**, fitted lag must equal actual published k−1. At k4, learned writer must be within 0.05 signed reward/scored decision of the BEST conventional arm. At k8 with the insufficient 4-record buffer, learned writer must exceed the BEST conventional by at least +0.05 original signed reward/scored decision. Only all scenarios passing yields `O16_PUBLIC_LEARNED_EVICTION_ADVANCEMENT_CANDIDATE_NOT_FIRST_USE`. Valid negative yields `O16_PUBLIC_LEARNED_EVICTION_NO_GO` with retained evidence, no retune. Any illegal actions, source drift, source/seed/reward budget breach, future info leak or capacity violation yields `O16_INVALID` and CI failure.

Require source-free tests before original execution, real Git SHA/blob custody, independently reconciled Linux and Windows original source/fit/reward hashes (float tolerance 1e−8), one complete FORGE public Go regression, and archived receipts. This publicly inspected original source is **NOT blinded independent first-use**; no promoted architecture, controller change, runner/queue addition, paid API or protected integration. Later independent source admission remains separate.
