# F110 — independently seeded public transfer with matched capacity

**Preregistration first:** commit `8a2d050435ca61e4ddca6faaa08cdd141742c1f7`, before F110 code, test construction or assessment. **Parent:** exact F109 branch head `1d3e0820002ed931f2a1a119ce5e52cd1467e9c8`. Preserve draft branch ancestry F99–F109.

## Why F110 is needed

F109 found Wingless F109 learned offset-dependent source routing at 48/48 against its 18-parameter query-only parent at 12/48 under identical 100-update and one-observation limits. But the newer model contained 64 learned parameters, versus 18 in the older model, and its favorable tests were generated from a single public synthetic source-offset family. Neither model-capacity superiority nor independent real-world generalization had been established. Yggdrasil's equally bounded strict slot-gate merely matched its soft gate, 48/48 against 48/48.

F110 uses three **new, disjoint, preregistered public** 48-pair diagnostic cohorts per lane; none are admitted as protected first-use or independent science. Every negative is retained. There is no post-test architectural selection, seed replacement or model refitting.

## Wingless equal-capacity and transfer controls

The original 64-scalar F109 source-offset router is retrained with its exact original 96 F109 public training pairs, for exactly 100 steps. A completely separate **64-trainable-parameter** baseline is also trained for 100 steps on those identical pairs. Its architecture has four independently trainable 4×4 query-conditioned attention heads, aggregated before selection of just **one** evidence value. This is a specific *offset-blind architectural ablation* of the F109 mechanism, not a proof that no other 64-parameter architecture could achieve the task. Both may read source metadata, but only the candidate's attention weights depend on the offset. The older 18-parameter query-depth selector and independently trained 18-parameter depth-blind control are also evaluated.

F110 freezes these three different public test generators:

- **W-A, 66200–66247:** differently shuffled source order, balanced offsets, ±1 signals and distractors.
- **W-B, 66300–66347:** ±1 queried signal with stronger, contradictory nonqueried distractors.
- **W-C, 66400–66447:** weak ±0.25 queried signal against ±1 and ±2 irrelevant observations.

Each case contains four source-tagged values and a public query depth plus source offset. Exactly one requested-source value flips sign in each counterfactual pair. Prediction reads one evidence value, not the entire array. Verify that permuting source offset *without changing observations* degrades the learned router's performance, so that the measured gain is at least causally related to the offset metadata.

**Frozen positive public screen:** in every 48-pair block candidate paired accuracy ≥0.75 and candidate minus equal-size query-only control ≥0.125; across 144 pairs ≥18 net candidate-only wins; worst offset group ≥0.60; incorrect offset intervention degrades paired accuracy ≥0.20; identical 64 learned parameters and one evidence-value read. All control arms and 144 per-pair decisions are retained. Do not claim improved parameter efficiency over the 18-parameter parent.

## Yggdrasil continued negative-or-positive assessment

Three more independent seed blocks, 66500–66547, 66600–66647, and 66700–66747, evaluate the original F103 trained soft slot-compatibility gate against F109's stricter equality-gated variant on 144 new public cases, without rewriting the model or allocating additional training. Both have the existing 20 learned scalars, 100 original updates and twelve graph edges. An independent variable-blind model and the coded strong oracle remain distinct controls. A positive Yggdrasil transfer screen requires ≥18 net strict-only gains; matching 144/144 is *not* improvement.

## Source custody and scope

The integrated workflow recomputes the true F109 current-run evidence from its F108 ancestry, checks its raw SHA-256 receipt, enforces the exact F109 public positive Wingless finding and negative Yggdrasil finding, trains the two 64-parameter Wingless models fairly, and archives all three fresh blocks plus per-pair results. The hosted Ubuntu/Windows integration and full Linux/Windows regression must pass. PR test-merge SHA qualification must never be described as literal direct-head qualification.

No new scheduler/controller, Codex, paid API, Work task, Cloudflare write, CKB-plane involvement, accepted refs, protected science, independent acceptance, source promotion or Wingless/Yggdrasil repository writes. This remains **bounded model-free public-development research**, not recursive scientific self-improvement or unattended GPT reasoning.