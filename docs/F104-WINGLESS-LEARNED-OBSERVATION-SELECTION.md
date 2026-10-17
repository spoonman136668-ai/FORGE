# F104 — learned query-gated observation selection (public-development only)

## Frozen lineage

The F104 contract was committed FIRST at `ef1f9c43d0703f441e466873359abb1715b6306c` before model/test implementation. It is the independently reserved `W100-C2` successor from F100, descendant of F103 `c0f205ceb8440f10f9b9179f0518abd900e6356e` (and F102/F101/F100/F99). Keep each draft ancestry intact; resolve prior dependencies before protected merges.

## Hypothesis and mechanism

A bounded selector trained only on 96 public paired counterfactuals can learn to read just **one out of four** publicly available depth-tagged observations for a requested reasoning depth, instead of using a coded depth match. For each pair, all four tag positions and distractor values are identical; only evidence at the requested depth flips sign. Each seed generates three cases; the third frozen seed block has 48 later public diagnostic pairs with deliberately rearranged observation order.

An 18-parameter model learns a 4×4 query-to-observation attention map plus readout scale and bias via 100 fixed, full-batch softmax/BCE SGD steps. Inference uses a **hard argmax selection of exactly one observation** and reads only that value, then applies the trained readout. No oracle or hidden target-depth label is passed to the learned selection function. The model is a deliberately narrow public toy, not an LLM, reusable trained cognition, or a native Wingless implementation.

Controls are independently trained same-capacity query-blind selector, permuted query, fixed first-slot and always-yes shortcuts, plus a coded exact requested-depth oracle strictly for ground-truth validation and standalone control. Outcome metric is paired accuracy: both positive and single-value-change negative must be classified correctly. The predeclared screen minima are 0.75 accuracy, +0.15 over blind, 0.60 worst requested-depth subgroup, and 0.50 fraction of public cases for which varying the query selects at least three different observed depth tags. Report all controls, including failures.

## Qualification and authority boundary

The existing Linux/Windows integrated CI includes adversarial tests and actual bounded CPU training, evaluated on the frozen diagnostic block, with content hashes of the source-bound reports. Full Linux and Windows regression remains required. The default PR-target synthetic merge commit is not the same identity as a direct branch-head qualification. Do not claim literal exact-head provenance until independently demonstrated.

No Codex, paid model API, scheduled Work task, new scheduler, Cloudflare change, CKB-plane integration, Wingless/Yggdrasil repository edit, protected scientific first-use, acceptance, promotion or unattended GPT invocation. Public development result is never independent scientific proof; preserve negatives and do not tune against assessment outcomes.
