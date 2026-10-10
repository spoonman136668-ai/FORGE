# FORGE public source boundary

The public code contains an audited subset of FORGE-only Go components and tests.

**Intentionally omitted:** private CKB-plane controller, all source-evidence ZIPs,
historical scientific artifacts, frozen donor source, accepted-ref/production
authority records, credentials, sealed cohorts, runner tokens and configuration.

These source-only contracts perform structural validation, not third-party
GitHub provenance authentication or permission to execute/accept science.

**FORGE Scientific Authority (FSA)** is the planned native FORGE decision
authority for FORGE-owned research. It is NOT CKB-plane's controller or
scientific authority, and is not yet implemented or activated. Historical
CKB source records remain in CKB's distinct authority domain; any FORGE
import must be authenticated and read-only. See
[ADR 0001](docs/ADR-0001-FORGE-SCIENTIFIC-AUTHORITY.md).

Mind-Palace retrieval is a separate, read-only, bounded advisory data flow
from its private repository. No Mind-Palace records or tokens are embedded
in public FORGE source, CI, or artifact logs.

Public GitHub Actions must use hosted Linux/Windows runners with read-only
permissions and no private-repository checkout. They do not demonstrate live
science, automatic generations, or a qualified external backend adapter.

Any future operational integration must independently establish source and
ledger provenance, exact pinned authority, prospective disjoint cohorts,
irreversible start receipts, terminal raw archives, one-shot execution,
bounded resource budgets, full integration regression, and controlled cutover.