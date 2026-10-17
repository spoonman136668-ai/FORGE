# F101-O — frozen answer-blind limited public-development language-to-roles contract

**Immutable qualified parent**: F100-O PR #386 head `d4bba4ce1b514d89a3fcb70812d40c32ba52818f`, GitHub Actions full Ubuntu and Windows regression run `38990005020`, with independent artifact readback and unchanged F95. F100-O whole KG source has 134,741 original triples; its public source is `tiantiangao7/kalm-qa` pinned at commit `826ee617e4da5b087584b0e03c70fe76642c6188`. F99-O established exact 2-hop and 3-hop public test population 14,872 and 14,274 (29,146 total).

**This exact frozen document is the first F101-O commit, before parser or tests.**

## Frozen parser scope

Build a self-contained Go package `noveltymechanisms/langroles` that accepts **only one natural-language question**, with **exactly one bracketed topic**, and an independently specified hop expectation (2 or 3). It returns an exact case-preserving root and a caller-independent predetermined ordered sequence of F100-O `largegraph.Step` typed roles and directions. No expected answer, answer tab or expected path is accepted. The function is deliberately a limited fixed-template semantic translator, not a language-model parser, trainable mechanism, generic MetaQA solver or scientific first-use.

Freeze **seven unambiguous exact public-development sentence grammars** (case-insensitive wording, whitespace-preserving case-sensitive topic, optional final question mark/period, no fuzzy/partial matching):

- 2-hop: `which person directed the movies starred by [TOPIC]` → `starred_actors:R, directed_by:F`.
- 2-hop: `the movies written by [TOPIC] were directed by who` → `written_by:R, directed_by:F`.
- 2-hop: `what types are the movies directed by [TOPIC]` → `directed_by:R, has_genre:F`.
- 2-hop: `which movies have the same actor of [TOPIC]` → `starred_actors:F, starred_actors:R`.
- 2-hop: `which movies share the same director of [TOPIC]` → `directed_by:F, directed_by:R`.
- 3-hop: `who wrote movies that share directors with the movie [TOPIC]` → `directed_by:F, directed_by:R, written_by:F`.
- 3-hop: `who acted in the films written by the screenwriter of [TOPIC]` → `written_by:F, written_by:R, starred_actors:F`.
- 3-hop: `what genres do the movies that share directors with [TOPIC] fall under` → `directed_by:F, directed_by:R, has_genre:F`.

**Correction of enumeration:** exactly **eight** frozen templates: five 2-hop and three 3-hop, not seven. Do not expand or tune this population during F101-O. Published public MetaQA descriptions and example questions motivate these, but cannot establish independence, a sealed benchmark, complete linguistic coverage, or semantic correctness in unobserved phrasings.

## Required strict abstention and data-flow controls

1. Require UTF-8, length 1–1,024 bytes, exactly one correctly paired bracketed topic with 1–512 UTF-8 bytes, no control/newline, and exact known template and hop count. Reject duplicate brackets, nested/extra brackets, punctuation inside slot, missing slot, unknown paraphrases, unsupported relations, extra clauses, lexical collisions and 2-vs-3 mismatch. Return a **typed abstention result** with no root, no steps and no inferred answer (and a bounded reason category); malformed source additionally fails closed.
2. Make source entity/topic case-sensitive: `[Film A]` and `[film a]` remain different. Grammar text only may case-fold ASCII. No guessed relation, auto-select, answer-informed changes, synonym expansion, paraphrase tolerance, label based filtering, cherry-picking, fallback to training answers, or post-split modification.
3. Adversarial unit tests: positive exact mappings for all eight frozen templates, direction inversion, changed topic case, grammar casing, unsupported rewording/no partial match, poisoning/extra clauses, topic ambiguity, invalid UTF-8/controls, hop mismatch, duplicate slots, safe parser output ownership and deterministic result. Require one negative too-far-frontier integration example with F100-O to prove bounded resolution still refuses overflow.
4. Real public corpus diagnostic: **read pinned original 2-hop test file Git blob `c60e27a75140cfc2792469181caca05b79b017ad` (14,872) and original 3-hop `09756f302c4100897c64144e7af8c73763cee4a2` (14,274) from immutable Git objects**, recheck Git object hash and exact original Git SHA. Invoke parser with **question text only**, physically discard answers *before* any parser invocation. Do not evaluate accuracy, compare answers, or call F100-O `Resolve` on this corpus. Preserve entire population; publish only aggregate parsed, abstained and reason counts, plus public source digest/commit metadata, never per-row questions, predictions, answers, or path strings from the corpus.
5. Tests must prove changing only answer columns leaves aggregate output unchanged. For real pinned corpus, answers may be present to validate line/column structure but are never read, decoded, compared or saved. Do not use test-question coverage results to modify templates during this F101-O gate.
6. Existing source-only GitHub Actions **push-triggered**, single Ubuntu/Windows matrix, read-only checkouts and external SHA/blobs. Focused unit tests, one required full Go regression per OS, vet, build, and SHA256-backed aggregate artifacts. No new scheduler/controller, no Codex, paid model, Work task, Cloudflare write, CKB integration, accepted refs, scientific dispatch, first-use, optimizer policy promotion or live deployment. Keep draft and preserve parent chain.
7. Outcome is **PUBLIC_FIXED_GRAMMAR_COVERAGE_ONLY**. A parsed path merely means a fixed template matched; it is **not** proof that a path answers the question, predictive accuracy, scientific novelty, independent blinded first-use, accepted research, model training, Dream-RSI/Pareto improvement or ThetaEvolve accepted learning.

The required gate is truthful whole-population coverage and abstention, including negative/zero coverage if the frozen templates mismatch. No tuning against held-out results. Follow-on F102-O may design a separate preregistered semantic adapter using **only** an authenticated development split and independent test custody, not retroactively reinterpret this public compatibility result.
