---
source_file: "optimizerstages/f90_signed_policy_observation.go"
type: "code"
community: "Community 3"
location: "L190"
tags:
  - graphify/code
  - graphify/EXTRACTED
  - community/Community_3
---

# AuditF90PreparedOutcomes()

## Connections
- [[F90Observation]] - `references` [EXTRACTED]
- [[F90ReadOnlyAudit]] - `references` [EXTRACTED]
- [[FrozenSixPolicyTrial]] - `references` [EXTRACTED]
- [[ReviewF91()]] - `calls` [INFERRED]
- [[TestF90MissingOutcomeSuppressesAllIPSEstimates()]] - `calls` [INFERRED]
- [[TestF90SourceOnlyRealAuthorityNeverInferred()]] - `calls` [INFERRED]
- [[TestF90TwoLaneSourceAndSignerIsolation()]] - `calls` [INFERRED]
- [[ValidateF89Pair()]] - `calls` [INFERRED]
- [[f90AuditLane()]] - `calls` [EXTRACTED]
- [[f90_signed_policy_observation.go]] - `contains` [EXTRACTED]

#graphify/code #graphify/EXTRACTED #community/Community_3