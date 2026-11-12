---
source_file: "fsaservice/read_only_test.go"
type: "code"
community: "Community 18"
location: "L48"
tags:
  - graphify/code
  - graphify/EXTRACTED
  - community/Community_18
---

# certFor()

## Connections
- [[TestDurableCheckpointAndWitnessCoherenceThroughMutualTLS()]] - `calls` [INFERRED]
- [[TestDurableWitnessRestartThroughIndependentMutualTLSServers()]] - `calls` [INFERRED]
- [[TestIndependentReadOnlyHandlersThroughRealMutualTLSClient()]] - `calls` [EXTRACTED]
- [[TestRSH03SixLaneReadOnlyAuthenticatedDualTLSWitness()]] - `calls` [INFERRED]
- [[TestSignedCheckpointHTTPRejectsMalformedForgedAndUnwitnessedWrites()]] - `calls` [INFERRED]
- [[TestSignedCheckpointWriteRequiresDistinctWriterMTLSAndWitness()]] - `calls` [INFERRED]
- [[cryptoed25519.PrivateKey]] - `references` [EXTRACTED]
- [[cryptotls.Certificate]] - `references` [EXTRACTED]
- [[cryptox509.Certificate]] - `references` [EXTRACTED]
- [[newGateFixture()]] - `calls` [INFERRED]
- [[newStepHTTPFixture()]] - `calls` [INFERRED]
- [[read_only_test.go]] - `contains` [EXTRACTED]
- [[testKey()]] - `calls` [EXTRACTED]
- [[testing.T]] - `references` [EXTRACTED]

#graphify/code #graphify/EXTRACTED #community/Community_18