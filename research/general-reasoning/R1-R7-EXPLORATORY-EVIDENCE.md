# General reasoning research — R1–R7 exploratory evidence
Date: 2026-11-01
Status: HISTORICAL SYNTHETIC PILOTS ONLY — not scientific acceptance, promotion, or production integration.
Custody: Research-only branch; no controller, owner, or runtime modification.

## Results
| ID | Setting | Main result | Limitation |
|---|---|---|---|
| R1 | 500 worlds; unknown XOR pair | Passive 90.3%; active 98.4%; 403 vs 484 perfect worlds | Correct hypothesis family provided; unmatched compute |
| R2 | 600 worlds; 44 candidates; XOR/AND/OR/majority | Passive 85.833%; active 97.222%; 215 active wins, 8 losses, 377 ties | All families known; 97,286 extra active hypothesis evaluations |
| R3 | 400 worlds; 200 novel parity worlds | Passive 65.583%; active library 67.75%; active + synthesis 100%; 200/200 novel detected | Parity synthesis grammar supplied; not invented; unmatched compute |
| R4 | 500 worlds; 8-bit parity; 5% label noise | Structured 100%; nearest neighbor 50.034%; constant 49.189% | Correct GF(2) representation supplied; 256 candidates |
| R5 | 400 worlds; four known families and unknown exactly-one-of-three | Adaptive 91.746%; nearest 76.306%; fixed logic 60.957%; unknown-family adaptive 58.730% vs nearest 71.888%; novelty TP 80/80, FP 2/320 | Fixed representations; uncalibrated novelty heuristic; unmatched compute |
| R6 | 300 worlds; 1,906 programs; 128 evaluations each | Guided 75.722%; random 70.972%; wins 147/84/ties 69 | Complexity-ordered search, not learned; total compute unmatched |
| R7 | 300 shifted threshold tasks | Guided 68.083%; random 71.222%; guided wins 66, losses 144, ties 90 | Shifted family, not proven mathematically outside candidate expressivity |

## Scientific interpretation
- R1–R5: Positive demonstrations within engineered synthetic spaces, NOT broad reasoning qualification.
- R6: Small in-distribution advantage for complexity-guided search.
- R7: Negative transfer result. Do not optimize the failed fixed heuristic without a new scientific hypothesis.
- Genuine novel primitive invention: UNVERIFIED.
- Equal-resource superiority over competent controls: UNVERIFIED.
- Cross-domain transfer, causal intervention, long-horizon reasoning: UNVERIFIED.
- No frozen external held-out benchmark or independent scientific acceptance was run.

## Source and result integrity manifest
These SHA-256 values describe the conversation-session local artifacts; **the original executable files and JSON results are not included in this commit**. This ledger is a summary, not a complete reproducibility package. Retrieve and commit original bytes before qualification.

| File | SHA-256 |
|---|---|
| reasoning_r1.py | da34647f32eb9f7efa2077ceb51d032df063c0d589dbbefba8338bd5e8cec0b9 |
| reasoning_r1_results.json | a23e4457d62f9b47c9bae3a196359f14a14f09ecc1e4d609f66609478ac5b255 |
| reasoning_r2.py | 94f05a79fd08f5ea0a71e559a8540bf8a39d6e77fc474b2b69c2ed346cabee86 |
| reasoning_r2_results.json | 483e4027bec8ae981fee986e068c580db2e9fc9b147651211663bf6f94e29645 |
| reasoning_r3.py | a0d33653bd633fb85ef045d8334760694987455132e74d5796a9ec53b6197bc6 |
| reasoning_r3_results.json | 6b98ae24be90a1c35ade43551963892e07ff408df98caa811915533628b0d99a |
| reasoning_r4.py | 62cd6087f6fa254f0e871d1bedcb4ebb98b78d964b6eba33896a9429111c758c |
| reasoning_r4_results.json | 20fbfb22136f62cbeb7548dec0ea26d32f6072d2595f5cc519e4c7d2a943c02c |
| reasoning_r5.py | 1b804e77264906f6a459ae2ed7a2a4efc0c03d94ee1479f6be34195155efe99f |
| reasoning_r5_results.json | 71cfc06f4071f5898004b463d8395bca4eac552be59f83549374c57b2f32e2fa |
| reasoning_r6.py | 1b247cce6a7c6c1028380059f7e765c18845c9e9d1b89020661c1a57958c7c77 |
| reasoning_r6_results.json | 606d1a110e7eaa59d0b03b19b5f854c213f915680e2e985c363854bbc3c551a9 |
| reasoning_r7.py | 4983d8dde00ccf8a3123f7706dc6575943cdd074ba75c46255545eefddaa6aed |
| reasoning_r7_results.json | f6edee9f9d2dca5d92474eb3c9198e08d3e76787b8c29ba394412360f50538c2 |

## Next scientific action
R8: test representation construction on genuinely held-out mechanism families, with source-verified original artifacts, compute-matched Bayesian/program-synthesis controls, frozen splits, explicit costs, and a negative-control check. No production promotion or integration is implied.
