#!/usr/bin/env bash
# Source-exact authentic MG02, GO R8 vs original Ygg R1. Never dispatch controller.
set -euo pipefail
cd "$GITHUB_WORKSPACE"
export PYTHONDONTWRITEBYTECODE=1
export PIP_DISABLE_PIP_VERSION_CHECK=1
export PYTHONHASHSEED=0

git merge-base --is-ancestor ffe3103fc451b248df23f118cb8ebeed85a02e8a "$GITHUB_SHA"
git merge-base --is-ancestor 1ed96adfb3e47773649a9113e103ebfa4189862b "$GITHUB_SHA"
git merge-base --is-ancestor ec6625b7413307d3005457bc1d937d7681faa172 "$GITHUB_SHA"
git merge-base --is-ancestor e91a0c7406e7dc88975d092214ef8314735e605a "$GITHUB_SHA"
git merge-base --is-ancestor 22642dc5713d0114f21584d68537b053137ec35a "$GITHUB_SHA"
test "$(git hash-object research/lcrm01/mg01_paired_live_minigrid.py)" = 49ca1b4b9b635f402f73e5f123f9e34093025cab
test "$(git hash-object research/lcrm01/mg01_paired_live_minigrid_preregistration.json)" = 6acf1e677e53ab4c2c29f55536a32661e3fc6af1
test "$(git hash-object research/lcrm01/mg01_ci.sh)" = f5164afd6e954e481076a43ae6bf684da6a09b94
test "$(git hash-object research/lcrm01/k4u_native_minigrid.py)" = 6a95bbef923ca7b27d18bd7d7937739a34b79a7f
test "$(git hash-object research/lcrm01/k4u_fetch_native_sources.py)" = 83f0d07b4a1bb1e1bbf0223ad563b93f67e09266
echo MG02_MG01_PROTECTED_ORIGINAL_SOURCE_EXACT

mkdir -p "$RUNNER_TEMP/mg02/minigrid" "$RUNNER_TEMP/mg02/wingless" "$RUNNER_TEMP/mg02/ygg-r12" "$RUNNER_TEMP/mg02/yggsrc"
python -m pip install 'pip==24.0' 'setuptools==69.5.1' 'wheel==0.43.0'
python -m pip install 'numpy==1.26.4' 'gymnasium==1.1.1' 'pygame-ce==2.5.3'

git init -q "$RUNNER_TEMP/mg02/minigrid"
git -C "$RUNNER_TEMP/mg02/minigrid" remote add origin https://github.com/Farama-Foundation/Minigrid.git
git -C "$RUNNER_TEMP/mg02/minigrid" fetch --no-tags --depth 1 origin 7f5853792ea7f04f75614661006d87fcf949f26d
git -C "$RUNNER_TEMP/mg02/minigrid" checkout --detach -q 7f5853792ea7f04f75614661006d87fcf949f26d
test "$(git -C "$RUNNER_TEMP/mg02/minigrid" hash-object minigrid/envs/empty.py)" = 8810bb0fa156d18475022edd8859b135ef745a5f
test "$(git -C "$RUNNER_TEMP/mg02/minigrid" hash-object minigrid/envs/fourrooms.py)" = d79f007e00f95f48284da66d760872483c02fab2
test "$(git -C "$RUNNER_TEMP/mg02/minigrid" hash-object minigrid/wrappers.py)" = 1eb2da8fb612653c97f443ff6c7492ed3f1aaa80
test "$(git -C "$RUNNER_TEMP/mg02/minigrid" hash-object minigrid/minigrid_env.py)" = eb29e9a902de0715ab77ec981a2113576d7664fa
python -m pip install --no-deps -e "$RUNNER_TEMP/mg02/minigrid"
echo MG02_PINNED_INDEPENDENT_AUTHENTIC_FARAMA_SOURCE_PASS

git init -q "$RUNNER_TEMP/mg02/wingless"
git -C "$RUNNER_TEMP/mg02/wingless" remote add origin https://github.com/spoonman136668-ai/Wingless.git
git -C "$RUNNER_TEMP/mg02/wingless" fetch --no-tags --depth 1 origin d89bf3a0fe057ceb2dfc9cfab2e2c24921220cdc
git -C "$RUNNER_TEMP/mg02/wingless" checkout --detach -q d89bf3a0fe057ceb2dfc9cfab2e2c24921220cdc
test "$(git -C "$RUNNER_TEMP/mg02/wingless" hash-object go.mod)" = 10b1d534f48e2a2723d22f4cb2c450a89d5658f3
test "$(git -C "$RUNNER_TEMP/mg02/wingless" hash-object research/native/itd02/r8/online_beliefs.go)" = 6857ecbef2d63f459a432a5d68c7edda2b5347c4
test "$(git -C "$RUNNER_TEMP/mg02/wingless" hash-object research/native/itd02/r8bridge/main.go)" = e14301e4307424eadb46865d7c1ede51f8bbe011
test "$(git -C "$RUNNER_TEMP/mg02/wingless" hash-object research/native/itd02/r5/policy.go)" = 239a5f2ab6d122b10cd5c7cc9388d154929b9888
(cd "$RUNNER_TEMP/mg02/wingless" && go build -trimpath -o "$RUNNER_TEMP/mg02/wingless-r8-bridge" ./research/native/itd02/r8bridge)
export MG02_WINGLESS_R8_BRIDGE="$RUNNER_TEMP/mg02/wingless-r8-bridge"
echo MG02_PINNED_ACTUAL_WINGLESS_R8_GO_BINARY_PASS

# Do not silently run Yggdrasil R12 on the six-field, 3-action MG01 lane.
# Its R10+R11+R12 source is inspected as its OWN exact original published code.
git init -q "$RUNNER_TEMP/mg02/ygg-r12"
git -C "$RUNNER_TEMP/mg02/ygg-r12" remote add origin https://github.com/spoonman136668-ai/Yggdrasil.git
git -C "$RUNNER_TEMP/mg02/ygg-r12" fetch --no-tags --depth 1 origin 6e2d4a219b1fb62e0124ba053b65b7e3fdd46546
git -C "$RUNNER_TEMP/mg02/ygg-r12" checkout --detach -q 6e2d4a219b1fb62e0124ba053b65b7e3fdd46546
test "$(git -C "$RUNNER_TEMP/mg02/ygg-r12" hash-object research/native/itd02/r10/public_adapter.py)" = 3917d36ce9f86a2c1b998a0a2f93fb27674a9205
test "$(git -C "$RUNNER_TEMP/mg02/ygg-r12" hash-object research/native/itd02/r11/affordance_cells.py)" = 614c7dfb1b43f485009b70cb85e9b7b5119cafc2
test "$(git -C "$RUNNER_TEMP/mg02/ygg-r12" hash-object research/native/itd02/r12/outcome_choice.py)" = 2d19b28d6d4db1988ae908fe91be1a27ce4c1907
echo MG02_YGGDRASIL_R12_SEVEN_ACTION_DOORKEY_REJECTS_OLD_SHARED_CONTRACT

# Original unchanged Ygg R1 source comes from MG01 authenticated K4U fetch.
python -B research/lcrm01/k4u_fetch_native_sources.py \
 --wingless-out "$RUNNER_TEMP/mg02/wingless-r1-unused.go" \
 --yggdrasil-out "$RUNNER_TEMP/mg02/yggsrc/native_policy.py"
test "$(git hash-object "$RUNNER_TEMP/mg02/yggsrc/native_policy.py")" = 3aa22b1e418a7f8cd9619c476f02b8c614917b16

export PYTHONPATH="$RUNNER_TEMP/mg02/ygg-r12:$RUNNER_TEMP/mg02/yggsrc:$GITHUB_WORKSPACE/research/lcrm01"
python -B -m unittest discover -s research/lcrm01 -p 'test_mg02_r8_paired_live.py' -v
echo MG02_EXACT_NATIVE_PUBLIC_INTERFACE_AND_R12_BLOCKER_PASS

# Two full distinct OS processes, each reconstructing original FIT and lives.
python -B research/lcrm01/mg02_r8_paired_live.py \
 --wingless-r8 "$MG02_WINGLESS_R8_BRIDGE" \
 --ygg-r1 "$RUNNER_TEMP/mg02/yggsrc" \
 --output "$RUNNER_TEMP/mg02/first.json" > "$RUNNER_TEMP/mg02/first.log" 2>&1 || {
 cat "$RUNNER_TEMP/mg02/first.log"; exit 1;
}
cat "$RUNNER_TEMP/mg02/first.log"
python -B research/lcrm01/mg02_r8_paired_live.py \
 --wingless-r8 "$MG02_WINGLESS_R8_BRIDGE" \
 --ygg-r1 "$RUNNER_TEMP/mg02/yggsrc" \
 --output "$RUNNER_TEMP/mg02/second.json" > "$RUNNER_TEMP/mg02/second.log" 2>&1 || {
 cat "$RUNNER_TEMP/mg02/second.log"; exit 1;
}
cat "$RUNNER_TEMP/mg02/second.log"
python -B research/lcrm01/mg02_r8_compare.py \
 --first "$RUNNER_TEMP/mg02/first.json" \
 --second "$RUNNER_TEMP/mg02/second.json" \
 --output "$RUNNER_TEMP/mg02/comparison.json"
python - "$RUNNER_TEMP/mg02/comparison.json" <<'PY'
import json,sys
d=json.load(open(sys.argv[1],encoding="utf-8"))
assert d["classification"]=="MG02_WINGLESS_R8_AND_YGGDRASIL_R1_PAIRED_LIVE_ORIGINAL_MINIGRID__NO_SCIENCE"
assert d["canonical_source_and_public_selected_trace_equal"]
assert d["yggdrasil_r12_not_connected"] and not d["scientific_first_use"]
print("MG02_SUCCESS_CANONICAL_SHA",d["canonical_original_public_trace_sha256"])
PY
test -z "$(git status --porcelain --untracked-files=all)"
test -z "$(git -C "$RUNNER_TEMP/mg02/minigrid" status --porcelain --untracked-files=no)"
test -z "$(git -C "$RUNNER_TEMP/mg02/wingless" status --porcelain --untracked-files=no)"
test -z "$(git -C "$RUNNER_TEMP/mg02/ygg-r12" status --porcelain --untracked-files=no)"
echo MG02_REAL_ORIGINAL_WINGLESS_R8_AND_YGG_R1_CONNECTED_R12_NOT_ADMITTED_NOT_SCIENCE
