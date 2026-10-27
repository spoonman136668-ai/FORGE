---
source_file: "fsaservice/signed_checkpoint_gate_test.go"
type: "code"
community: "Community 18"
location: "L78"
tags:
  - graphify/code
  - graphify/EXTRACTED
  - community/Community_18
---

# newGateFixture()

## Connections
- [[AuthorityHandler()]] - `calls` [INFERRED]
- [[Initialize()]] - `calls` [EXTRACTED]
- [[NewCheckpointGate()]] - `calls` [INFERRED]
- [[NewClient()]] - `calls` [EXTRACTED]
- [[NewObservedAuthority()]] - `calls` [INFERRED]
- [[Provision()]] - `calls` [EXTRACTED]
- [[Provision()_1]] - `calls` [EXTRACTED]
- [[TestDurableEpochStepJournalWithDualMutualTLSAndRevocation()]] - `calls` [INFERRED]
- [[TestSignedCheckpointGateRejectsInvalidSourceAndExternalBinding()]] - `calls` [EXTRACTED]
- [[TestSignedCheckpointGateRequiresWitnessBeforeAcknowledging()]] - `calls` [EXTRACTED]
- [[TestSignedCheckpointGateSerializesDuplicateProposals()]] - `calls` [EXTRACTED]
- [[TestSignedCheckpointGateWitnessLagPoisonsWithoutRetry()]] - `calls` [EXTRACTED]
- [[TestSignedCheckpointHTTPRejectsMalformedForgedAndUnwitnessedWrites()]] - `calls` [INFERRED]
- [[TestSignedCheckpointWriteRequiresDistinctWriterMTLSAndWitness()]] - `calls` [INFERRED]
- [[WitnessHandler()]] - `calls` [INFERRED]
- [[certFor()]] - `calls` [INFERRED]
- [[gateFixture]] - `references` [EXTRACTED]
- [[newStepFixture()]] - `calls` [INFERRED]
- [[newStepHTTPFixture()]] - `calls` [INFERRED]
- [[signedArchiveHead()]] - `calls` [EXTRACTED]
- [[signedHighwater()]] - `calls` [EXTRACTED]
- [[signed_checkpoint_gate_test.go]] - `contains` [EXTRACTED]
- [[testCA()]] - `calls` [INFERRED]
- [[testKey()]] - `calls` [INFERRED]
- [[testService()]] - `calls` [INFERRED]
- [[testing.T]] - `references` [EXTRACTED]

#graphify/code #graphify/EXTRACTED #community/Community_18