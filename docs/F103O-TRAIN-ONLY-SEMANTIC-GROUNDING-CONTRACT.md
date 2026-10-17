# F103-O — preregistered TRAIN-only semantic grounding audit

**Prerequisite:** F102-O #390 exact source head `f2f6618a78a194b361d996f6984b32472189a858`; hosted dual-OS acceptance `38993141072`; 233,176 authentic public TRAIN questions, syntactic matches 48,051, not correct answers. Preserve all prior F98-O—F102-O source identities and developer/test partition. This contract is committed **before implementing evaluator or reading any answer label** in the new gate.

## Scope & permitted original source

Public development and diagnostic evaluation **ONLY**, never prospective independent first-use. Input immutable original third-party `tiantiangao7/kalm-qa` at commit `826ee617e4da5b087584b0e03c70fe76642c6188`, specifically:
- KB: `metaqa/original/kb.txt`, original Git object `a43fa7ca5e6894236556f2984764070c4ca5562b`, 134,741 original edge rows, SHA256 `9b4d3b3066266075ad1577b4beed68e6e112e76e1a29ed2cb00a2896d2b792af`.
- TRAIN two-hop: `metaqa/original/2-hop/qa_train.txt`, original Git object `d2ce0a9f3670769f4239baa4eb6bf7bdc91d9468`, 118,980 rows.
- TRAIN three-hop: `metaqa/original/3-hop/qa_train.txt`, original Git object `77409d56af8d1fde7a4bec23cf5e1df1e0a08e59`, 114,196 rows.
- **Prohibit opening/reading original TEST QA objects** in this gate (F101 already exposed the test pool; they are NOT an independent scientific holdout).

## Frozen mechanism and score classes

Retain F100-O independent source-native directed `largegraph` index, 7 MB / 150k row / 50k entity / 128-role / 512B field original ingestion limits, 4,096-node frontier and 1—3 exact roles, hard nontruncating failure. Retain **F102-O frozen 46 TRAIN-derived plus eight F101 templates unchanged**. For every original training row, split the line at the first TAB; the **parser receives only question text**, never the answer label, answer set, candidate target or scoring feedback. After the parser resolves a complete typed-role sequence via F100-O graph, an independent **read-only comparison** may inspect original TRAIN answers only in its isolated scorer; this is the first F103 permitted use of TRAIN labels. No parser adaptation, rule edit, role selection, graph modification, optimized cutoff or source-specific answer heuristic after label viewing.

Freeze answer comparison as follows: original answer cell `a|b|...` represents an unordered *set of exact case-sensitive strings*, with no trimming, case-folding, stemming, aliasing, learned mapping, ontology closure, comma parsing, interpretation or partial match. Reject an empty answer, empty member or repeated duplicate label as malformed QA source **rather than silently excluding**, and still publish the full expected cohort denominator before fail-closed. An exact-set score requires **all predicted targets equal all answer set members**. Secondary *gold-set overlap* requires at least one predicted target is a gold answer; report as a non-primary diagnostic and never as full accuracy. No prediction-vs-answer compare for abstained, unknown-root, empty-target or over-budget rows. Explicit row categories are mutually exclusive and denominator-preserving:
1. `parser_abstained` (unsupported grammar, malformed question, hop mismatch, invalid topic)
2. `graph_budget_refused` (entire frontier rejected without truncating)
3. `graph_missing_or_no_targets` (no reachable targets or root)
4. `graph_resolved_exact_set` (nonempty whole set equals gold set)
5. `graph_resolved_partial_overlap` (nonempty intersection but not equal)
6. `graph_resolved_disjoint` (nonempty candidates and zero overlap)
Capture `graph_resolved_ambiguous` as *auxiliary subset* of the three resolved categories when candidate count greater than one, never double count category denominators. Preserve raw gold member count and source row totals, duplicate source rows stay counted. Any missing row, malformed answer, nonexact pin or unexpected parser/output status invalidates **the entire audit**. Publish **only aggregate counts and exact source digests**; no question strings, labels, target strings, paths, or per-row diagnostics in outputs or CI logs. No answer accuracy over abstentions, no ranking, no always-hit/nearest-target story.

Adversarial fixture tests: exact set vs subset vs disjoint, ambiguous target sets, duplicate labels denied, source cohort malformed label denied, source identity sha mismatch denied, parser answer perturbation unchanged, case-sensitive answer matching, reversed role direction and unknown root, 4,096/4,097 frontier boundary, determinism of aggregate counts under row permutation and duplicate rows, no mutable graph exposure, no per-row leak. Use synthetic examples only in code tests; live original cohort answer cells only in host transient evaluation of aggregates.

## Hosted qualification and acceptance

Commit immutable design before any executable changes. Existing branch-push-only GitHub-hosted Ubuntu+Windows. Read true **Git object bytes** by `git show HEAD:path`, hash all 3 original Git blobs and source commit at runtime before running evaluator (Windows worktree CRLF cannot affect values). Each OS: focused Go adversarial tests, real full 233,176-row train-only development audit, check complete denominator and flags, one Go full regression, vet and build. SHA256-manifested aggregate JSON artifacts, independent cross-OS comparison. Do not add scheduler or privileged runner; no Codex, paid model inference, CKB-plane coupling, Cloudflare write, optimizer accepted-ref mutation, protected scientific dispatch, Dream-RSI/Pareto promotion, ThetaEvolve accepted training. Keep draft and unmerged pending ancestry/review.

**Disposition:** `PUBLIC_TRAIN_ONLY_GROUNDING_DIAGNOSTIC` whether result good or negative. TRAIN semantic compatibility is NOT prospective novel scientific correctness, independent blind first-use or validated generalization. A future external, genuinely unexposed and independently custodied holdout requires a separate qualification, frozen rules, and authorization before scientific score.
