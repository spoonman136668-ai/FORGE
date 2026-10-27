---
source_file: "optimizerstages/f89_six_arm_policy.go"
type: "code"
community: "Community 3"
location: "L110"
tags:
  - graphify/code
  - graphify/EXTRACTED
  - community/Community_3
---

# PrepareF89Selection()

## Connections
- [[F89FreezeDigest()]] - `calls` [EXTRACTED]
- [[F89PreparedAssignment]] - `references` [EXTRACTED]
- [[FrozenSixPolicyTrial]] - `references` [EXTRACTED]
- [[TestF89DualLaneSeparationNoSharedOwnerOrDraw()]] - `calls` [INFERRED]
- [[TestF89EveryArmUniformExactAndNonAuthorizing()]] - `calls` [INFERRED]
- [[TestF89PreparedIdentityAndPermissionTamperingFailsClosed()]] - `calls` [INFERRED]
- [[TestF89RejectUnfrozenOrReusedPolicies()]] - `calls` [INFERRED]
- [[TestF89RejectionThresholdAndUntrustedRandomness()]] - `calls` [INFERRED]
- [[ValidateF89Freeze()]] - `calls` [EXTRACTED]
- [[ValidateF89Prepared()]] - `calls` [EXTRACTED]
- [[f89Arms()]] - `calls` [EXTRACTED]
- [[f89AssignmentDigest()]] - `calls` [EXTRACTED]
- [[f89Draw()]] - `calls` [EXTRACTED]
- [[f89_six_arm_policy.go]] - `contains` [EXTRACTED]
- [[f90SyntheticRows()]] - `calls` [INFERRED]
- [[io.Reader]] - `references` [EXTRACTED]

#graphify/code #graphify/EXTRACTED #community/Community_3