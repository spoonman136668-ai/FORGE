# ELG-01A9B — bracket-free prefix structure induction (October 23, 2026)

**Classification:** bounded CPU development experiment, negative against a matched symbolic control. **No original scientific first-use, promotion, controller dispatch, runner allocation, workflow/authority change, or protected-branch mutation.** This document and its branch are inert archival material; FORGE issue #798 remains advisory, not an F139 executable work order.

## Objective and actual implementation

Compared to ELG-01A9, the experiment removes **the supplied AST from the model's input**. All model arms receive raw, bracket-free prefix sequences of lexical symbols and operator identifiers and full target sentences. On 1,104 training examples (384 single-leaf, 720 two-leaf) the candidate infers lexical width, which tokens act as operators, operator arity (among 1–4), lexical mappings, connective choices, and binary order/reversal. No gold parse trees, gold operator boundary labels, or per-subtree text targets are supplied to the models. Evaluation comprises 192 synthetically generated **five-leaf** nested compositions from seed 20261024. This is *new local development source*, not independently born original scientific source and not an untouched evaluator-held set.

The model is **not unconstrained grammar learning**: prefix input format, candidate arity range, role-coded lexemes, finite connectives and a two-child text realization scheme are hypothesis-class priors. Its parse is deterministic once the arity is identified. Generator/scorer know the actual structure, although models see only flat token sequences.

## One final complete local development regression (following focused tests)

| Arm | Exact five-leaf outputs /192 | Median serial generation for 192 (ms) |
|---|---:|---:|
| Induced-prefix candidate | 192 | 2.003 |
| Separately implemented equal-hypothesis symbolic control | 192 | 1.614 |
| GRU autoregressive, seed 13 (45 epochs) | 0 | 7.129 |
| GRU autoregressive, seed 29 (45 epochs) | 0 | see full local results |

**7/7 isolated pytest checks PASS**, including disjoint train/dev source identities, parser inference without input AST, independently implemented equally informed comparator, tamper-detecting oracle, and malformed-source rejection. **11/11 standalone invariants PASS**; one final complete local experiment PASS. The GRU controls receive the same raw source and text pairs but are neither convergence-matched nor equal-compute, and the Transformer was not retrained. No claims of superiority against a fully trained conventional language model are justified.

The **strongest equally informed comparator ties accuracy and is faster in this run**; therefore **NO scientific or engineering Pareto advancement**. The candidate merely demonstrates that a restricted compositional hypothesis class can be identified from controlled whole-sequence examples.

## Reproducibility, provenance and custody

- **Runnable, standard-library-only symbolic reproducer committed here:** [`reproduce_symbolic.py`](./reproduce_symbolic.py). Run `python reproduce_symbolic.py`. Git blob SHA: `970468932395f2515d1df8920ab157ed80c54ac3`, verified byte-identical to the locally tested file.
- Train input SHA-256: `60def7bb0b70971403baac5e7303cdcff34c406fc23ee738697ff5b1e37acdba`.
- Development input SHA-256: `28c925ec38c6bd6a95f135522c243e9b3bf4eb51d9065184fab81b55e651fc55`.
- Full local experiment source `a9b_experiment.py` SHA-256: `cb3534cf167b5dc74b0837e28a8805125b68e397bdadb7c7e9ef4df50f4c54ef`.
- Local complete `results.json` SHA-256: `febc8a5414eba0251e0281c0257f9fbc69d4845a5aa2f175a65580b583d1fd28`.
- Local final regression log SHA-256: `802f300774e69a5a2d185d255c8069c636d5014905cc2a510528aa9099b6fe02`.
- Local complete source/test/results archive SHA-256: `f8bf69af8d304c8c0b7d700b18f66104fe99a4faf09043491a2e7fcddb794622`.

**Custody limit:** This branch contains the independently runnable symbolic reproducer and this results record. The complete PyTorch GRU experimental source, test files, and raw results are currently in a separate local archive, not in this Git branch; hashes alone are NOT complete reproducibility. The symbolic reproducer confirms the 192/192 candidate result and exact train/dev identities, but does not run the GRU negative experiment.

## Next development boundary

Do not keep optimizing this now-solved prefix task or present the same shape-heldout cases as an untouched external test. Require a genuinely heterogeneous, non-prefix/ambiguous input family, strong equally-informed *learned* controls and resource parity, with a task where a hand-coded symbolic hypothesis class does not already reach the ceiling. Keep this finding and all negative cases as development history only. No FORGE-native scientific admission is implied.
