# NR-M1V — Native task-effect scores versus an independent conventional Bayesian control

**Current status:** source-only algorithm equivalence assessment; no original MiniGrid execution, no source-first-use, no native release integration or automatic model admission.

## Immutable scientific custody

- Frozen hypothesis **before code** in `PREREG.json`, commit `0098081227aa37d8ab2ed8c1811a3c1b7f7686eb`.
- Original exact engineering-qualified Yggdrasil local-cell candidate [draft #700](https://github.com/spoonman136668-ai/Yggdrasil/pull/700), SHA `8a1bf9c961a1c9b66080885d4d48106836638b5e`, `research/native/itd02/mg40/task_cells.py` Git blob `fdccd7a601adfacf4a4f8533279e66280cf16d99`. Its `TaskCell` class is **copied as an unchanged source excerpt** to `pinned_native_taskcell.py`, with the original source pin; it does *not* instantiate original worlds or change the qualified Yggdrasil branch.
- Independent Wingless Go native candidate [draft #438](https://github.com/spoonman136668-ai/Wingless/pull/438), SHA `ac433699db5e66db798836d10c7dc0488f57ae3c`, `mg40/task_effect.go` Git blob `21c408972791c1968b1e26d1a9a24e73b75f63db`. Its `score` and `Propose` use the *same integer equation and candidate ordering* as the Yggdrasil class, but the executable test here is **only the literal pinned Yggdrasil class extract**; Wingless Go original code isn't executed or newly qualified by this gate.
- Wingless source-review issue [#439](https://github.com/spoonman136668-ai/Wingless/issues/439) remains open and unapproved. Its source acceptance authority is independent of FORGE research. No attempt to use a second account, AI or self-review to fabricate approval.

## What is being compared

Both the Yggdrasil local-cell task-effect score and the Wingless Go task-effect score are:

```text
score(n,k) = floor(10000 * (k+1) / (n+2))
```

where `n` counts only **completed, selected, same-public-context actual actions**, and `k` counts selected observations whose *engineered public task-effect label* was positive. The quantity before quantization is **exactly the conventional Beta(1,1) Bernoulli posterior predictive mean** `(k+1)/(n+2)`. Therefore this score is *not a new inference estimator*.

The independent control in `audit.py` uses Python's `Fraction` exact rational mathematics to compute the Beta posterior, then applies the same declared 10,000-point floor/thresholds as the native implementation. Crucially, it receives the **same counts, consequences, context, parent proposal and available actions**; no privileged state, hidden original goal or synthetic reward advantage.

The complete bounded audit checks all possible histories `0 <= k <= n <= 6` for action 3 (pickup), action 5 (toggle), and whichever parent action (of seven) is proposed; covers count-cap boundaries up to 4096; and measures exactly matching proposals, abstentions and override counts. No memory trained or improved through an actual world in this test.

## Limitations and decision

**If the source-pinned exhaustive regression has zero disagreement**, it establishes equality of this *score and fixed decision policy* to a perfectly legitimate conventional Bayesian count learner at the checked bounds, **not** a proof that Yggdrasil's distributed architecture as a whole equals a Bayesian model, or that no richer native learner can improve. The native implementation's original selected-feedback custody, local cells, cold checkpoints and performance/resource costs are separate engineering properties. The engineered public door/target-effect labels themselves remain hand-coded semantic assumptions rather than independently discovered causal rules.

For genuine scientific advancement, the next authorized first-use experiment must compare actual native *learning and policy returns* to a trained same-information Bayesian/control, model-based and recurrent alternatives under frozen new source cohorts, cold retention, and per-action CPU/memory/storage budgets. Any unqualified source comparison is **NO-GO**. Do not promote a neural-native/nontransformer claim from shared Beta posterior arithmetic.

Run source-free tests: `python -m unittest discover -s research/nr-m1v -p 'test_*.py' -v`. Independently see bounded actual counts: `python research/nr-m1v/audit.py --output nr-m1v-results.json`. Standard dual-OS FORGE CI is required for exact-head engineering PASS.

**Noninterference:** All work additive on a FORGE draft research branch. No native policy branch, protected main, existing FORGE F139 controller/autonomy, scheduled queue, accepted-model registry, original Farama environment or source-owned first-use changed.
