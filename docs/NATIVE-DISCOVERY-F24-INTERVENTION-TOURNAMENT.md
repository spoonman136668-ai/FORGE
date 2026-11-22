# Eureka F24 — Contradiction-directed intervention tournament (DEV)

**Frozen November 9, 2026 (Eastern), before F24 implementation, tests or scores.** Existing inactive draft PR #1614 exact parent \`abaf92fb3c72ebc72ebc0e0a200c3b5c0213096c\`. Preserve every F10–F23 result and negative, particularly \`F23_DEV_NO_GO\` (1/4).

## Hypothesis and distinct mechanism

Can a **causal hypothesis tournament** choose scarce action interventions when persistent early and recent causal explanations disagree *only under intervention*, improving unfamiliar return-world causal prediction over conventional active-learning controls? F23 altered prediction via archive retrieval; F24 alters **action choice** while **every** selector uses the *same last-16-credited MAP prediction model* for scoring. The candidate's persistent model is used for intervention selection, not covertly for scoring forecasts. All policies learn from their own real actions and delayed consequences.

## Frozen worlds and observations

Four synthetic DEV arms: seed \`163\` or \`167\` × cues \`balanced\` or \`skewed\`. Each policy runs independently for exactly 128 real actions with intervention action1 cap 12; action0 is passive. Generator-only 8-bit rules: 163 A=0xc6, B=0x19, C=0x72; 167 A=0x5a, B=0x87, C=0x31. A steps 0–31, B 32–63, C 64–95, return A 96–127. Consequence: \`((rule>>cue)&1) XOR (action & ((rule>>(cue+4))&1))\` (F20 256-rule family). Balanced public cue: \`f12Mix(seed ^ uint32(t+1)*0x27d4eb2d)&3\`; skewed: \`(t/5+seed%2)%2\` except every fifth step \`(t/5+seed%4)%4\`. Erasure iff \`f12Mix(seed ^ 0x31415926 ^ uint32(t+1)*0x9e3779b9)%13==0\`; else flip iff \`f12Mix(seed ^ 0x27182818 ^ uint32(t+1)*0x85ebca6b)%17==0\`. Two-step-delayed **actually selected action** consequence is revealed before decision t; exactly 126 credits and 2 pending after 128. No learner accesses hidden law, phase, future cue, uncredited outcome or counterfactual scorer labels. No first-use seed (including 59/83) permitted.

All models use the same uniform 4×4 cue-pair factors over 256 rules, 8:1 likelihood, tie-to-zero MAP, correct action attribution, and only credited records. Every score forecast uses the same most-recent-16-credits MAP, even for candidate; trajectory differences arise solely from intervention actions.

## Frozen policies, all max 12 real interventions

- **tournament candidate:** compare the predictive bit probabilities under action1 versus action0 between an early fixed 24-credited-record posterior and a recent last-16 posterior. Intervene if \`abs(Pearly(y1=1)-Precent(y1=1))-abs(Pearly(y0=1)-Precent(y0=1)) >= 0.20\` **and** fewer than two recent-16 action1 credits for the current cue. While fewer than 24 credits exist, explore at t divisible by 8. Otherwise passive; never exceed 12.
- **bayes-ig:** last16 posterior binary entropy(action1) > entropy(action0).
- **bayes-error:** last16 posterior classification uncertainty(action1) > uncertainty(action0).
- **two-window:** action1 vs action0 disagreement gain between recent8 and recent24 posterior >=0.20, without persistent early archive.
- **thompson:** deterministic sample from the current cue-pair posterior by \`f12Mix(seed ^ uint32(t+1)*0x165667b1)\`; action1 iff sampled pair has a causal action effect.
- **periodic:** action1 at t%10==0.
- **random:** action1 iff \`f12Mix(seed ^ uint32(t+1)*0x9e3779b9)%9==0\`.
- **no-intervention ablation:** always action0.
- **wrong-credit ablation:** same tournament policy but credit the opposite action to fitted causal factors, while applying and logging *real* actions and outcomes.

All policy instances have identical step/cue exposure, action options, evidence delay, max intervention budget, and posterior capacity. Report work counts and elapsed time as diagnostic only, not end-to-end cost proof. No hindsight best-of-control selector decides candidate actions.

## Predeclared scoring and stopping

At decision-time checkpoints t=96,104,112,120, after due credit and before action, independently score all **8 counterfactual grid points** (four cues × both actions) of current return-A law against the *common last16 MAP* from each policy's own real history. Scorer-only truth cannot flow back to learner. Four checkpoints = 32 maximum correct; preserve each checkpoint, full 32-bit trace, all actual actions and consequences, intervention counts, compute-work, and canonical SHA-256 digests. Snapshot full ledger immediately after step95 (96 seen, 94 credits, 2 pending); independently reload it and complete steps96–127; require byte-identical terminal state, score traces, action logs and 126/2 final lineage. Do not retune based on development results.

**F24_DEV_SIGNAL_UNVERIFIED only if ALL four arms:** candidate >=+2/32 versus the strongest of six conventional controls (bayes-ig, bayes-error, two-window, thompson, periodic, random), >=+3/32 versus both no-intervention and wrong-credit ablations, actual intervention count 2..12, and source/negative/cold-credit integrity verified. Every other outcome is \`F24_DEV_NO_GO\`; ceiling controls also yield NO_GO. No oracle or post-result threshold adjustment. Strong controls are conventional online heuristics, **not** a proof of superiority over Bayes-optimal planning. This is synthetic developmental evidence only: first-use, SCIENTIFIC_PASS, autonomous improvement, deployment, and end-to-end efficiency remain unverified.

## Engineering/authority limits

Append only \`docs/NATIVE-DISCOVERY-F24-INTERVENTION-TOURNAMENT.md\`, \`nativediscovery/f24_tournament.go\`, and \`nativediscovery/f24_tournament_test.go\` to the existing PR #1614. Preserve this protocol as a **separate ancestor commit before implementation**. Do one final branch ref update after implementation to avoid redundant automatic CI. Focused local Go/race/vet is not original full engineering acceptance; final exact-SHA original Linux+Windows 8/8 full tests/race/vet/build and frozen F4 2/2 remain mandatory. Do not alter existing workflows, tests, G141 180s cap, main, owners, research lanes, controllers, queues, runners, schedulers, paid APIs, CKB-plane, first-use, merge or deployment. G141 regression belongs to the independent FORGE regression workstream.