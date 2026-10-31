# ACC-G102 — Certified confidence-triggered early exit: frozen CPU pre-screen

**State at registration:** preregistered *before* implementation and any G102 measurements, on G91–G106 GPU LLM-bottleneck research draft PR #1329. This synthetic CPU recurrent-score mechanism is NOT a TinyLlama model, GPU accelerator, trained decoder, or scientific admission. Base FORGE main `0810ecf3df6378bcbfe5239d30df836b7e12a602`. Independent of the GPT-2 CPU stream.

## Mechanism and exactness proof

Let `D=64`, `L=12`, `V=128` and `h_0=x`. At each layer `h_(l+1)=tanh(W_l @ h_l)`; accumulate output token scores `s += U_l @ h_(l+1)`. The greedy token is the lowest-index maximum of the **full 12-layer score**. For any future layer, each hidden component is in [-1,1], so `|U_l[v] @ h_(l+1)| <= sqrt(D)*||U_l[v]||_2`. Offline precompute `B_l=max_v sqrt(D)*||U_l[v]||_2`, then `R_l=sum_{j>l} B_j`. If the current top-two score gap `g` is **strictly greater** than `2*(R_l + 1e-10*(1+R_l))`, the partial top token must equal the final top token regardless of unknown future hidden states. Candidate stops only with this deterministic bound; otherwise evaluates subsequent layers. Recheck every produced greedy result against the exact full decoder, including negative controls. No probability confidence heuristic or inaccessible oracle future state can certify a skip.

## Frozen cost controls

- NumPy float64, exactly one BLAS thread. Seeds `[10201,10202,10203]`, 8 independent normal initial hidden states each. For each seed/regime generate independent `W` arrays [12,64,64] with `N(0,1/sqrt(64))`, and independent `U` arrays [12,128,64] from the same distribution.
- Two fixed regimes: `iid` negative control leaves all output matrices unscaled; `early_dominant` deliberately favorable sets all U layers **after** the first to 1e-6 times their independently drawn values. No real-model structure is inferred.
- **48 total cases** (3 seeds ×2 regimes ×8 queries). Baseline evaluates all 12 recurrent hidden updates and score contributions. Candidate computes every charged recurrent/score contribution until its bound certifies the winner; pays norms (when computed), margin selection, checks, and all realized layers. Precompute U row-norm bounds and suffix sums once per model, report setup ms separately. No target-output leakage.
- Warm each arm once, then record **7 alternating paired timing trials** per query. Record baseline/candidate ms, score parity, number of layers evaluated, bound at stop, observed margin, true full-reference top-2 margin and actual speedup. All 48 greedy winners must match exactly; record any missing/nonfinite scores as FAIL.
- Freeze exploratory conditional PASS only if **both** IID and favorable regimes have median baseline/candidate speedup `>=1.15×` across their 24 cases, and **all 48 outputs are exactly equal**. Otherwise **`NO_GO_SYNTHETIC_SCREEN`**. Favorable-only speedup is a negative outcome.
- Legitimate candidate promotion requires genuine contextual transformer behavior (including invariant causal mask and actual model logits), trustworthy certified bounds without uncharged work, held-out next-token parity, full GPU model throughput, optimized baseline, and separate first-use scientific qualification.

The screen must preserve immutable case JSON and CI/provenance with failures. No paid API, runner/controller duplication, protected main mutation, model deployment, thresholds changes or scientific admission. Revisions after observations require a new versioned preregistration.
