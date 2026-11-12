# F98-O — first genuine external public benchmark source for FORGE optimizers

**Scope:** Optimizer research only. Not the FORGE autonomy workstream's already merged **F98** historical-provenance gate. This opt-in source audit does not touch controllers, Cloudflare, scientific originals, or CKB-plane. Mind-Palace is read-only advisory context.

## Distinct achievement: a source that FORGE did not author

Rather than constructing another synthetic "independent" signature or writing source-visible toy tests and renaming them as unseen, F98-O reads three **real, existing, third-party public** data files: the original MetaQA movie knowledge graph and the original 2-hop and 3-hop *test* splits, mirrored in the independently maintained [KALM-QA repository](https://github.com/tiantiangao7/kalm-qa). This source was publicly committed in **2019**, before F95 was developed. The [original MetaQA dataset](https://github.com/yuyuz/MetaQA) was published as a multi-hop knowledge graph QA benchmark.

The readback is pinned, not a live floating download:

- Third-party repository: `tiantiangao7/kalm-qa`, exact commit `826ee617e4da5b087584b0e03c70fe76642c6188`.
- Original knowledge graph Git blob: `a43fa7ca5e6894236556f2984764070c4ca5562b`.
- Original 2-hop QA test Git blob: `c60e27a75140cfc2792469181caca05b79b017ad`; expected **14,872** questions.
- Original 3-hop QA test Git blob: `09756f302c4100897c64144e7af8c73763cee4a2`; expected **14,274** questions.

GitHub Actions checks out that **public third-party repository** using the existing read-only GitHub permission, compares all three exact Git objects, validates the entire bounded UTF-8 corpus/row counts, computes SHA-256 of real bytes and emits aggregate structural compatibility metadata. No source data are copied to FORGE, published in artifacts, or ingested into scientific training. The diagnostic artifact contains only digests, counts and non-authorizing observations.

## Important negative result: F95 cannot yet be fairly scored on all MetaQA test items

F95's current `noveltymechanisms.Compile` accepts **128 triples** and only identifiers fitting `[a-z0-9_-]{1,48}`. MetaQA's real KB is much larger and uses movie/person names with spaces and capitalization. The test questions are **natural language**, not a supplied frozen sequence of typed graph roles. A script that filters to the expected answer's neighborhood or derives its path using the answer itself would leak the label, giving false accuracy.

Therefore F98-O deliberately **does not call the F95 model, produce a benchmark accuracy figure, claim a scientific win, or select a favorable subset**. It reports actual compatibility blockers and preserves the complete external population denominators. It does not call a model, Codex, paid inference, or any untrusted script from the public repository. Python only reads the three pinned data files.

An independently preregistered, answer-blind translator from questions to role sequences, exhaustive bounded subgraph extraction, fixed evaluation budgets, source custody, valid matching comparison methods and genuine pre-outcome release are necessary before attempting a legitimate accuracy comparison.

## Why public external does not mean a blinded scientific holdout

The corpus is genuinely sourced externally, and its historical Git source can be independently checked. But it has long been public; a mechanism developer can inspect it. Its historical timestamp and matching Git blobs **do not** prove independent preregistration of this FORGE experiment, non-exposure of the benchmark during method development, a witness, scientific first-use or out-of-distribution generalization. A validated public corpus can be used for transparent, source-authenticated **development compatibility** research only. **F97's future externally witnessed/sealed first-use is still open.**

For live science, FORGE's separate scientific-authority pathway must handle independent pre-outcome custody, frozen one-use eligibility, unseen cohort retention, complete negative outcomes and release; the optimizer workstream cannot self-certify these. F99–F102 descendant research and autonomy branches remain untouched.

**Disposition:** Real independent-origin source validation and honest mechanism-interface feasibility, not a genuine prospective scientific original. Dream-RSI/Pareto promotion, ThetaEvolve accepted-outcome training, science dispatch, Cloudflare writes, accepted refs and new credentials stay denied. PR may remain draft if ready-for-review triggers paid automatic Codex usage.
