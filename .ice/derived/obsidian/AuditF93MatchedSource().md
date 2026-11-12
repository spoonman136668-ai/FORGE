---
source_file: "optimizerstages/f93_matched_block.go"
type: "code"
community: "Community 3"
location: "L252"
tags:
  - graphify/code
  - graphify/EXTRACTED
  - community/Community_3
---

# AuditF93MatchedSource()

## Connections
- [[F93MatchedBlock]] - `references` [EXTRACTED]
- [[F93MatchedPlan]] - `references` [EXTRACTED]
- [[F93SourceReview]] - `references` [EXTRACTED]
- [[FrozenSixPolicyTrial]] - `references` [EXTRACTED]
- [[TestF93MissingOriginalOrIncompleteBlockBlocksComparisons()]] - `calls` [INFERRED]
- [[TestF93NoPosthocPlanRehashOrCrossLaneReuse()]] - `calls` [INFERRED]
- [[TestF93SyntheticPositiveDoesNotEstablishPolicyGain()]] - `calls` [INFERRED]
- [[TestF93TamperedBlocksFailClosed()]] - `calls` [INFERRED]
- [[ValidateF93MatchedPlan()]] - `calls` [EXTRACTED]
- [[auditF93Lane()]] - `calls` [EXTRACTED]
- [[f93_matched_block.go]] - `contains` [EXTRACTED]

#graphify/code #graphify/EXTRACTED #community/Community_3