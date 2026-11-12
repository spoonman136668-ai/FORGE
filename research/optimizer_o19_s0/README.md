# Optimizer O19-S0 — guaranteed retrieval feasibility, source only

## Scope and source custody

This is an **analytical, original-source-grounded engineering investigation**, NOT new original experiment use, source-fit/heldout qualification, scientific first use, or an O19 outcome claim.

Pinned upstream: `proroklab/popgym@410d5aa626dae8024f498354d8781a0d1870c399`, `popgym/envs/repeat_previous.py` Git blob `5d43f3c97a7af43450dc898096ca7b8a660251b5`. The original `RepeatPrevious(num_decks=1,k=8)` returns public suit observations and later signed reward for the suit from seven source steps ago. Shared source-own step loop has 51 actions and reads prediction before the memory write. This yields 44 reward-scored source steps (t=7..50). We do **not** import POPGym or inspect/step hidden source deck, source RNG, future information, source roles, FIT, CHECK or DEV.

Prior Optimizer O18 PR #824, exact source head `0922fed1dac1e1056edc8a1bf39f45cdc12106de` and protocol-only FIRST `3f0e4a58404ab5d8ed260017b1a3f11737afea0d` are historical. Original research reported **`O18_PUBLIC_RECORD_CREDIT_NO_GO`**, k8 candidate signed rewards `[-0.070,-0.366,-0.407]` versus trained-stride `[+0.165,+0.189,+0.188]`. These are *historically reported*, not independently authenticated by this source-only branch: original push-run artifact ID/SHA remains to be recovered. All earlier O18 original source FIT/DEV roles must be considered **consumed**. Never trigger a rerun from this code or alter the frozen O18 negative.

## Exact bounded finite-horizon finding

The DP enumerates retained timestamp subsets (`≤4` records) over t=0..50, rewarding 1 exactly when timestamp `t-7` is still retained before read. Once a timestamp was queried its content has no future genuine RepeatPrevious use, so the analytical DP may drop it before a write. This **relaxes** the original source writer which only evicts when writing; hence DP is an upper bound on *guaranteed direct stored-timestamp hits* for any four-slot source policy. The DP examines 4,532 time/state combinations and proves the maximum **26 of 44** guaranteed direct recalls.

A separately programmed **fully source-writer-legal** clock-only policy chooses to write the first 4 of every 7 public time steps; on insertion at capacity it replaces only a timestamp already queried. It attains the same 26 direct recalls with capacity ≤4, so the upper bound is tight, WITHOUT accessing any actual suit or private card/reward. This represents a legal deterministic combinatorial comparator, not trained learner quality. Ordinary readout on a missing timestamp can still correctly guess/infer a suit. Thus **26/44 is NOT a success-rate or source-returned reward ceiling**, and it does not guarantee native-vs-control improvement.

## Scientific interpretation / next prospective O19 work

A rigorous new O19 native mechanism cannot simply widen O18's reward-eligibility window, retune on consumed O18 DEV, or compare only against a weak FIFO baseline. A distinct falsifiable candidate is **source-feedback-linked record-survival attribution**, with lineage of public memory writes, reads and evictions, and updates strictly from legitimately observed action and signed reward. Unlike O18's unweighted mean of all previous eligible write gradients, any proposed attribution must identify which recorded information was actually retrieved, and reject accidental positive reward where a missing target was only guessed. The lineage itself consumes memory and CPU and must be included in total resources.

Before any new original source use: source owner preregisters a NEW, disjoint and unfamiliar task family, source roles/identity, sufficient calibration info, independent conventional full-capacity memory/recurrent/credit/replay and deterministic periodic comparator, frozen stop rules and total cost accounting. Strong controls get identical public observations, training experiences, legal actions and signed rewards, including common public lag-fitting if used. Exact original source/fit/heldout custody stays with existing owners; no new F139/controller/CKB/FSA writer/scheduler, protected merge or paid API.

The O19 proposal is **not admitted science**: `O19_S0_ANALYTICAL_FEASIBILITY_ONLY / O18_NO_GO_IMMUTABLE / O19_ORIGINAL_NOT_EXECUTED / SCIENTIFIC_GO_FALSE`.

## Reproduce (Python 3.11 standard library)

```
python -B -m unittest discover -s research/optimizer_o19_s0 -p 'test_*.py' -v
python -B research/optimizer_o19_s0/o19_capacity.py
```

The deterministic emitted JSON is `o19_result.json`; seven source-free tests guard exact capacity, DP replay, source-legal construction, monotonicity and full/one-slot controls. No network access or source import required.
