---
type: community
cohesion: 0.20
members: 14
---

# Community 188

**Cohesion:** 0.20 - loosely connected
**Members:** 14 nodes

## Members
- [[dot-CommitSnapshot()]] - code - watchdog/persistent.go
- [[Incident]] - code
- [[LoadPersistent()]] - code - watchdog/persistent.go
- [[LoadPersistentForWriter()]] - code - watchdog/select.go
- [[PersistentLedger]] - code - watchdog/persistent.go
- [[SelectAndCommit()]] - code - watchdog/select.go
- [[TestInvalidShadowBatchDoesNotRecord()]] - code - watchdog/select_test.go
- [[TestShadowLedgerRejectsTrailingData()]] - code - watchdog/persistent_test.go
- [[TestShadowLedgerSurvivesProcessRestart()]] - code - watchdog/persistent_test.go
- [[TestShadowSelectionSurvivesRestart()]] - code - watchdog/select_test.go
- [[persistent.go]] - code - watchdog/persistent.go
- [[persistent_test.go]] - code - watchdog/persistent_test.go
- [[select.go]] - code - watchdog/select.go
- [[select_test.go]] - code - watchdog/select_test.go

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Community_188
SORT file.name ASC
```

## Connections to other communities
- 4 edges to [[_COMMUNITY_Community 21]]
- 1 edge to [[_COMMUNITY_Community 142]]
- 1 edge to [[_COMMUNITY_Community 97]]

## Top bridge nodes
- [[SelectAndCommit()]] - degree 7, connects to 2 communities
- [[TestShadowLedgerRejectsTrailingData()]] - degree 3, connects to 1 community
- [[TestShadowLedgerSurvivesProcessRestart()]] - degree 3, connects to 1 community
- [[TestInvalidShadowBatchDoesNotRecord()]] - degree 3, connects to 1 community
- [[TestShadowSelectionSurvivesRestart()]] - degree 3, connects to 1 community