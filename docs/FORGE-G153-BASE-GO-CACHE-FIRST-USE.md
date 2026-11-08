# RAR-G153 — qualified-main compiler cache seed for source-changing Go (one-use DEV)

## Freeze before implementation
- Protected base main: `1363cadc0f20155798ef52d72f85ac6df8a81ed6`, tree `61d683215b4c7be8e9a4db921f04a15354279152`, original full Linux/Windows 8/8 PASS CI #42533958664 in 118s; F73 origin PASS #42533958893.
- Branch `engineering/rar-g153-base-go-cache-seed-first-use-20261108`, exactly these six changed paths and no more:
  1. `docs/FORGE-G153-BASE-GO-CACHE-FIRST-USE.md` (this preimplementation freeze)
  2. `.github/workflows/qualify.yml`
  3. `scripts/check_rar_g145_pr_scope.py`
  4. `scripts/check_rar_g148_go_cache.py`
  5. `scripts/check_rar_g153_base_cache_dev.py` (new)
  6. `nativediscovery/g153_compiler_cache_dev_test.go` (new harmless Go test)
- G148 original full original commands and test inventory, F139, GenEnv, Linux race shared cgroup <=4GiB, Windows G144 Job Object <=4GiB, source/negative controls and both required status checks remain unchanged; no owner, runner, scheduler, scientific first-use, queue, Cloudflare, CKB-plane, paid APIs or other projects touched.
- Historical G151 source `c10f92742ec4d7ffdb42f613ce19045f6945a804` / tree `933b7fdbce51e258be1eb8c47676036461e348e2` is a **closed NO_GO** (CI #42534448906). Its `G148_HEAD` binding missing from both pre/post steps was reproduced and 15/15 mutated static contract negatives were rejected independently in the G152 read-only audit. G151 never reached base-cache restore. Do not replay or relabel G151 as success.

## Immutable hypothesis and experimental conditions
- On a **new Go source graph** under a source-verified same-repository main-target development PR, Go's compiler cache may reuse content-addressed action objects from qualified protected-main when restored by one literal exact key **without** reusing test results or bypassing original source checks. A newly added Go test changes the graph and runs in the complete original suite.
- Trusted protected-main compiled-input graph `39c27c4f51e81fb12d3b5dc573a99793d80c1b692943d7fbb9ed9cd7501cad47`; exact literal key `rar-g148-win-go-db3730bf1158ebde65edf14ced6077aaf11ff6b3267f56377207d0432a3b3d2e` with verified protected-main HIT #42533958664 and original full tests PASS. Main cache is read-only seed, not a replay of old test results.
- G148's current changed-graph exact-key restore **must MISS**; G153 then restore only that exact authenticated main cache key with `actions/cache/restore@v4` and **no restore-keys**. Preflight must validate `G148_HEAD` and `G153_HEAD` from the true PR head SHA, event base SHA and tree, exact six-file diff, G145/G148 frozen admissibility, original resource flags, graph inequality, cache key and path. Postflight must confirm exact base HIT, nonempty <=2GiB cache, stable worktree, same current graph, and emit a DEV provenance receipt before any original Go tests. A static self-test must reject missing/wrong head, base cache key, hit status, wrong branch/repo, fallback path or step order.
- One first-attempt full **8-job** existing CI; unchanged `go test -count=1 ./...`, `go vet ./...`, `go build ./...`, Linux regular/race `-count=1`, isolation and negative controls, all original F139/GenEnv/Promptbreeder, resource limits, provenance. Frozen thresholds: end-to-end <=132s (2x vs historical 264s); Windows native <=127s; Windows three source jobs <=244s; Linux three <=200s; six combined source <=449s. Fail closed if unavailable, slow, test failure, scope drift, or wrong cache hit; **no retries and no post-result adjustment**.
- If all first-use engineering gates pass: mark DEV_POSITIVE only, close the development PR **unmerged**; if any fails: record NO_GO, close **unmerged**, preserve failure. Production main-safe dynamic baseline-key implementation would need new separate authorization/qualification. No learning/RSI/scientific claims regardless of engineering CI outcome.
- Original real-world comparisons: source-changing Eureka cold 150s #42530723806 vs identical Go graph docs-only warm 105s #42533357042 (different hosted hardware; observed, not strictly causal).
