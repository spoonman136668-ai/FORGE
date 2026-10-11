# R19J — One integrated qualification on the inherited stack

Exact parent: `92a4e01f588dbebd32e2f4da75d027569e4a10e6`. This workflow re-runs four executable pinned CKB-versus-FORGE differential scripts **in one checkout**, with full Go regression, vet, build, Linux race and Windows tests. It verifies the exact upstream CKB file blobs and refuses any unexpected source replacement.

Acceptance requires both GitHub-hosted OS jobs success at the same SHA. This proves only the finite tested common-subset behaviors: R196 progression scenarios, R1 shortlist scenarios including signature collisions, R6 multibatch scenarios, and R7 historical source-attestation scenarios. It is **not** full CKB scientific controller parity, protected external custody, fresh disjoint scientific input, F4 original authorization, live FORGE control, a branch merge, or retirement authority for CKB. The exact scripts are run unchanged.

Do not merge or enable dispatch on the strength of this suite. Outstanding blockers remain documented in issues #20 and #44. No CKB or KTRADE mutation.
