# R19K — consolidated merge-readiness inventory (source-only)

## Authenticated Git state on 2026-10-11

- FORGE main exact SHA: `fc50538f7d9151721299ffbb1ccfbb018354c08f`.
- Integrated R19J source SHA: `496c07a9ad94f86e71d3abc5df05b2e66494d7f1`.
- GitHub compare main → R19J: `ahead_by=59`, `behind_by=0`, `files_changed=149`. This is **not** a small R18/R19-only delta: it includes Dream-RSI, FSA, ICE, reference fixture copies, workflows and the R18–R19 sequence.
- Exact integrated qualification: GitHub Actions run `38176200155`, both hosted Linux and Windows PASS. Tests are synthetic and source-only.

## Decision

**Do not merge the 59-commit inherited stack wholesale into main under a claim of R19 migration completion.** The stack contains distinct FSA and research-control surfaces with independent requirements, not only the 20-odd evolutionary portfolio increments. The draft PR chain remains unmerged.

The bounded accepted engineering subset is `evoportfolio/`, its test-only comparison commands/scripts, and frozen upstream reference code. R19J qualifies it **in the context of the full stacked tree** but does not establish minimal transplant qualification onto main.

## Next safe promotion sequence

1. Pin the exact main and source Git trees, files and dependency manifest. Split out a branch based on main carrying only the *bounded* portfolio packages and selected test harnesses; do **not** include `dreamrsi/fsagate`, live FSA issuers, F4 original-run controls, or controller authority.
2. Apply import/compile closure against base main, with no opportunistic authorizations or fixture changes; record every copied immutable source blob.
3. On the exact transplant tree, run focused Linux/Windows tests, all-Go regression, vet/build, Linux race, and the existing executable CKB R196/R1/R6/R7 parity suite. Review every mismatch as a potential integration defect.
4. Require explicit review/approval of the separately scoped PR before merger. No activation, F4 original launch, source admission, or CKB retirement follows from merge.
5. Physical independent first-use and authenticated external evidence custody remain blocked by issue #20, and inheritance coverage by issue #44.

Status: **inventory documented; transplant not yet implemented, reviewed or promoted**. No live research/CKB/KTRADE changes.
