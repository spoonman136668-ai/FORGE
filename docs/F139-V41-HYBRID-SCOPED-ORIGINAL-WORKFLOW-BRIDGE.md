# F139 Hybrid PR #1660 — exact original-owner workflow bridge (source only)

The existing protected-main V41 owner source is 1a40fe4e3ec6e93a1631d59863b95e90981d734e. This change
**adds exactly one job** to existing `.github/workflows/f139-v41-original-owner-live-install.yml`, with no
new Actions event, new scheduled task, controller, queue, or worker.

The new job is gated by the original owner, existing issue #807, exact
first-attempt original self-hosted Windows runner, and the separate paired
approval prefix `F139-HYBRID-V41-PAUSE-RESUME `. No live original-owner
maintenance occurs unless this PR is separately authorized and merged,
protected-main push qualification passes, and an authenticated pair of
original-owner approval comments is created.

Source admission is restricted to PR #1660, branch
`engineering/f139-hybrid-reader-route-20261110`, original base `1a40fe4e3ec6e93a1631d59863b95e90981d734e`,
the original owner workflow blob `b7abc3a9118a5c69dd24b4f351bf5697bfdf52f3`, and one full
new blob `ff11352d1d298361e97b1e7422338f608d4b2a70`. The complete existing PR source-file change set
is frozen in the G145 code. G148/G156 permit only this explicit scope.
Generic changes to CI workflows remain rejected.

The job runs the already qualified same-task paired-backup wrapper from
merged protected main, with read-only token permissions and no checkout
credentials. The wrapper verifies the original V41 SID, database and
two-lane policy and produces a fresh cold backup and detached recovery,
then resumes the same existing task if safe. Source CI is not original-owner
execution, source promotion, Hybrid lane admission or scientific first-use.
