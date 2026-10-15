# R11 — learned WHEN to retain memory, after R10 independent negatives

## Frozen scientific reason

R10 tested different 16-weight methods on untouched 26xxx Wingless development cohorts and independently verified both **negative**:

| Candidate | Mean worst-generator gain vs hard-minimax | All-three-fold gate |
|---|---:|---|
| W36-C2 gradient conflict projection | −0.052662 | FAIL |
| W36-C4 fixed hardest-example 96-slot episodic memory | +0.018229 | FAIL |

R10 [original development review #38663053332](https://github.com/spoonman136668-ai/FORGE/actions/runs/38663053332), pinned original review artifact `11939807429`, SHA-256 `754a3a924efaeb9cdf4ca99998391d0a02d1224bf8bc43bf6ac764ea934c2031`.

**The next mechanism is not an alternate learning rate for C4.** R11 tests whether the system can learn which experiences to retain rather than retain the highest-loss 32 per source at every epoch.

## Frozen R11 method

A new shared 16-weight classifier and 3 learned source-retention logits operate with exactly **32 persisted examples/source, 96 total**. Each of 32 epochs on *training data only*:

1. Hold a deterministic rotating 1/5 of the available training rows aside as a **train-only proxy** (never the future validation/heldout rows).
2. Construct two ephemeral 32-slot candidate retention sets from the other training rows: highest current loss; and source feature-coverage buckets (two highest-loss examples per dominant feature index, fill deterministically).
3. Estimate the one-step loss difference of the two retention schemes **on the train-only proxy**, and update the corresponding source-specific learned logit. The logit selects the proportion of a single 32-slot retained memory allocation between these two operators. Every retained set is size 32.
4. Update the classifier from the selected memories. There are no extra model/AI API calls, queries, variable-budget exploration or access to future fold labels.

Controls: existing, source-pinned hard-minimax 32-epoch shared learner; and the unchanged R36 C4 hard-loss 96-slot memory under identical 32-epoch, 3×576 source training examples. **Accounting caveat:** the learned policy has 3 extra trainable controller scalars and additional counterfactual proxy computation. Do not claim precisely equal trainable-parameter counts or compute until measured. Equal persistent *example-memory capacity*, model dimension and epochs are established.

## Data separation and admissibility

New Wingless developmental seeds 28000–28015, 28032–28047 and 28064–28079, train each 16-seed block separately and evaluate on the other two blocks (32 held-out **development** seeds). Reserved and **untouched**: 28200–28247 future sealed; 29000–29015, 29032–29047, 29064–29079 prospective replication training; 29200–29247 prospective sealed.

Preregistered developmental success requires worst-source gain ≥2 percentage points against hard-minimax **in each of the three folds**, no source harm greater than 5 points, candidate overall accuracy ≥55%. C4 and hard-minimax remain reported regardless of signs. A negative must not lead to retrospective retuning. Positive development is only advisory, not authorization.

## Independent witness

The R11 independent job **does not import the R11 controller, original worker, R34 evaluator, or R36 library**. It reconstructs all actual 3×576 examples from pinned native Wingless; independently reruns all 32-epoch model updates, proxy-loss-based memory decisions, learned logits, and both controls; independently recomputes each of the three-arm × three-fold × 32-seed scientific row results from the native generator and weights. Fingerprints and every classifier/gate decision are compared. It checks that 96 retained examples, no source drift, the exact negative R10 parent, and no first-use mutations hold. It records real positive/negative results without asserting scientific acceptance.

## Autonomy and FSA boundary

This is genuine train-only developmental research, NOT a new sealed scientific original. R8 previously proved two real once-only Wingless originals can automatically chain; **no R11 first-use authority is created by this PR**. Source-only and independent witness must pass before a future operator-authorized prospective launch. No new scheduler/controller/FSA witness, Cloudflare provisioning, paid API, KTRADE/CKB-plane/Yggdrasil scientific identity changes, or replay of consumed R7/R8 originals. Yggdrasil remains architecturally independent.

**Next direction if negative:** learned trainable compression of invariant relationships and retrieval, not more handcrafted retention heuristics. Independent source-structure generalization cohorts required for substantive progress.
