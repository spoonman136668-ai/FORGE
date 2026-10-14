# R29B single-use qualification

R29's first-use is consumed and never replayed. Its GitHub run 38489235357 failed prior to scientific execution because FORGE's repository-scoped token cannot read a private CKB-plane Actions run. R29B has a distinct scientific identity and fresh, disjoint preregistered development/holdout seeds.

The CKB wake run is independently inspected by the operator through the connected private repository. A signed-in GitHub repository-owner comment must explicitly attest to the selected private wake run and authorize exactly one R29B original; the public FORGE workflow checks that comment and has no private CKB read credential. The witness is owner attestation, not independent FSA authorization. Do not activate a new scheduler, change CKB-plane authority, or repeat a consumed scientific original.

Source-only qualification must prove GitHub Issue-comment read permission **before** creating any irreversible R29B claim. After a first-use launch, an interrupted original is quarantined, never automatically rerun. Only an independently reviewed result can produce an R30 proposal.
