#!/usr/bin/env bash
# MG01: source-exact original MiniGrid / independent Go + local-cell contract.
# No FORGE controller, no CKB-plane, no generated miniature environment.
set -euo pipefail
cd "$GITHUB_WORKSPACE"
export PYTHONDONTWRITEBYTECODE=1
export PIP_DISABLE_PIP_VERSION_CHECK=1

git merge-base --is-ancestor 51b3a936e74a3132c40252f97af1c1b084d62703 "$GITHUB_SHA"
git merge-base --is-ancestor 00978a0c6725fc4a7fb9e14af2fa15a8cdec64e5 "$GITHUB_SHA"
git merge-base --is-ancestor e3f4484a8b425019bc83d822983361b5802190d9 "$GITHUB_SHA"
git merge-base --is-ancestor c85c40aca7ea5ca9609ca78246f95b76738f6f95 "$GITHUB_SHA"
git merge-base --is-ancestor b0d4359c16be6eaea3be7e901bb3f35cdebcbe9d "$GITHUB_SHA"
git merge-base --is-ancestor fbdef59ac1e8c013dea4e1e5fa73e9b3469f9c4b "$GITHUB_SHA"
test "$(git hash-object research/lcrm01/k4r_frozen_independent_minigrid.json)" = cf87447b6eb47b33757a98ea6622ce2ea40bd022
test "$(git hash-object research/lcrm01/k4u_frozen_native_minigrid.json)" = dd3b6a746e0ed5e5804832288b8310647f9c5f62
test "$(git hash-object research/lcrm01/k4r_minigrid_source.py)" = a09f73d528192f41e1e9572d9b8476a66cdff644
test "$(git hash-object research/lcrm01/k4u_native_minigrid.py)" = 6a95bbef923ca7b27d18bd7d7937739a34b79a7f
test "$(git hash-object research/lcrm01/k4u_fetch_native_sources.py)" = 83f0d07b4a1bb1e1bbf0223ad563b93f67e09266
echo MG01_FROZEN_ORIGINAL_SOURCE_CHRONOLOGY_PASS

mkdir -p "$RUNNER_TEMP/mg01/minigrid" "$RUNNER_TEMP/mg01/go/wingless" "$RUNNER_TEMP/mg01/yggsrc"
python -m pip install 'pip==24.0' 'setuptools==69.5.1' 'wheel==0.43.0'
python -m pip install 'numpy==1.26.4' 'gymnasium==1.1.1' 'pygame-ce==2.5.3'
git init -q "$RUNNER_TEMP/mg01/minigrid"
git -C "$RUNNER_TEMP/mg01/minigrid" remote add origin https://github.com/Farama-Foundation/Minigrid.git
git -C "$RUNNER_TEMP/mg01/minigrid" fetch --no-tags --depth 1 origin 7f5853792ea7f04f75614661006d87fcf949f26d
git -C "$RUNNER_TEMP/mg01/minigrid" checkout --detach -q 7f5853792ea7f04f75614661006d87fcf949f26d
test "$(git -C "$RUNNER_TEMP/mg01/minigrid" hash-object minigrid/envs/empty.py)" = 8810bb0fa156d18475022edd8859b135ef745a5f
test "$(git -C "$RUNNER_TEMP/mg01/minigrid" hash-object minigrid/envs/fourrooms.py)" = d79f007e00f95f48284da66d760872483c02fab2
test "$(git -C "$RUNNER_TEMP/mg01/minigrid" hash-object minigrid/wrappers.py)" = 1eb2da8fb612653c97f443ff6c7492ed3f1aaa80
test "$(git -C "$RUNNER_TEMP/mg01/minigrid" hash-object minigrid/minigrid_env.py)" = eb29e9a902de0715ab77ec981a2113576d7664fa
python -m pip install --no-deps -e "$RUNNER_TEMP/mg01/minigrid"
echo MG01_INDEPENDENT_FARAMA_MINIGRID_GIT_SOURCE_PASS

python -B research/lcrm01/k4u_fetch_native_sources.py \
 --wingless-out "$RUNNER_TEMP/mg01/go/wingless/policy.go" \
 --yggdrasil-out "$RUNNER_TEMP/mg01/yggsrc/native_policy.py"
printf 'module mg01\n\ngo 1.25.0\n' > "$RUNNER_TEMP/mg01/go/go.mod"
cp research/lcrm01/mg01_wingless_native_bridge.go "$RUNNER_TEMP/mg01/go/main.go"
(cd "$RUNNER_TEMP/mg01/go" && go build -trimpath -o "$RUNNER_TEMP/mg01/wingless-bridge" .)
export MG01_WINGLESS_BRIDGE="$RUNNER_TEMP/mg01/wingless-bridge"
export PYTHONPATH="$RUNNER_TEMP/mg01/yggsrc:$GITHUB_WORKSPACE/research/lcrm01"
python -B -m unittest discover -s research/lcrm01 -p 'test_mg01_public_only.py' -v
echo MG01_WINGLESS_GO_YGG_LOCAL_EQUAL_PUBLIC_FIELDS_PASS

# Reproduce original source interactions twice in independent Python OS
# processes; no reuse of intermediate learner memory or heldout response.
python -B research/lcrm01/mg01_paired_live_minigrid.py \
 --wingless-binary "$MG01_WINGLESS_BRIDGE" \
 --yggdrasil-source-dir "$RUNNER_TEMP/mg01/yggsrc" \
 --output "$RUNNER_TEMP/mg01/first.json" > "$RUNNER_TEMP/mg01/first.log" 2>&1 || {
 cat "$RUNNER_TEMP/mg01/first.log"
 exit 1
}
cat "$RUNNER_TEMP/mg01/first.log"
python -B research/lcrm01/mg01_paired_live_minigrid.py \
 --wingless-binary "$MG01_WINGLESS_BRIDGE" \
 --yggdrasil-source-dir "$RUNNER_TEMP/mg01/yggsrc" \
 --output "$RUNNER_TEMP/mg01/second.json" > "$RUNNER_TEMP/mg01/second.log" 2>&1 || {
 cat "$RUNNER_TEMP/mg01/second.log"
 exit 1
}
cat "$RUNNER_TEMP/mg01/second.log"
python -B research/lcrm01/mg01_compare.py \
 --a "$RUNNER_TEMP/mg01/first.json" \
 --b "$RUNNER_TEMP/mg01/second.json" \
 --output "$RUNNER_TEMP/mg01/comparison.json"
python - "$RUNNER_TEMP/mg01/comparison.json" <<'PY'
import json,sys
r=json.load(open(sys.argv[1],encoding="utf-8"))
assert r["classification"]=="MG01_TWO_INDEPENDENT_NATIVES_LIVE_ORIGINAL_MINIGRID_CONNECTED__NO_SCIENCE"
assert r["canonical_source_and_live_trace_agree"]
assert r["canonical_sha_agrees"]
assert not r["scientific_first_use"] and not r["scientific_accepted"]
print("MG01_NATIVE_CONNECTED_TO_ONE_AUTHENTIC_ENVIRONMENT",r["classification"])
PY
test -z "$(git status --porcelain --untracked-files=all)"
test -z "$(git -C "$RUNNER_TEMP/mg01/minigrid" status --porcelain --untracked-files=no)"
echo MG01_ORIGINAL_SOURCE_AND_BOTH_NATIVES_PASSED_WITH_NO_SCIENTIFIC_ACCEPTANCE
