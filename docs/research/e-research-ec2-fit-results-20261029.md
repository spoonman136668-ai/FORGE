# E Research E-C2 — FIT reproduction baseline

Date: 2026-10-29. Advisory only; not independently accepted science.

Isolated 16x16 ecological simulator, six FIT seeds 31000-31005, four arms, three development generations and one evaluation episode, 80 steps each. Within-episode reproduction splits parent energy equally at a threshold of 1.6, up to 12 organisms. No extra energy created. 24 evaluation runs plus development episodes. Numerical checks and deterministic replay PASS. Maximum energy/resource conservation residual 1.735123156265672e-11.

Descriptive median harvest / median births / median active steps:
- Evolving, dynamic: 3.2475 / 0 / 472.5
- Evolving, static: 1.2940 / 0 / 326
- Random-parent, dynamic: 0.5350 / 0 / 249.5
- Greedy, dynamic: 27.24 / 6 / 860.5

Median harvest per acting step: dynamic-evolving 0.0068744, static-evolving 0.0031346, random-parent 0.0021617, greedy 0.0316555. Median survivors: 4.5, 0.5, 0, and 12 respectively. Evolving organisms did not reproduce in the median evaluation, and greedy control dominates. Evidence of adaptive evolution, acquired intelligence or unfamiliar transfer NOT SUPPORTED. Equal effective organism-step exposure has not been established.

Local source SHA-256: 1b3159224711ba46c4ef847fcce7ec1eff06ac6cd76e87d912461bf3cbe78154. Local results JSON SHA-256: 3c963f8ff91d2b6e2bdb0360e5ac4c0088d05129622c09a7a7c356d07c2a6293. Original files remain outside this draft PR, so repository-only reproduction and FORGE FSA original custody UNVERIFIED. No FORGE autonomy or model-selection change.

Next: E-C3 matched exposure and strong policy-search controls. Preserve negative finding; do not treat reproduction mechanics as emergent intelligence.
