# CI failure triage adapter R1

The `citriage` adapter converts **one exact known GitHub Actions failure class** into an advisory repair-registry query: FORGE's Linux `Public isolation` step. All other failures return an error, not a guessed repair. GitHub run IDs and commit SHAs are identifying fields, not proof; upstream must independently verify the GitHub API data and immutable run provenance.

Use: authenticate an immutable CI run and failed step externally; pass the identified facts to `citriage.Diagnose` against a pre-provisioned and verified repair registry. The result is reference-only, not a repair operation. Any proposed repair still requires bounded diff review, exact SHA regression on Linux and Windows, and explicit scientific-authority separation.

This does not fetch GitHub logs, change workflows, schedule retries, launch Codex, or execute science.
