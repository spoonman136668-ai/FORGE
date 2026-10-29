#!/usr/bin/env bash
# Source-exact MG05 authentic Farama native-only development; no controller.
set -euo pipefail
cd "$GITHUB_WORKSPACE"
export PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 PIP_DISABLE_PIP_VERSION_CHECK=1

git merge-base --is-ancestor f4e08d27776248f6f075db6fb93d3f4195bd941c "$GITHUB_SHA"
git merge-base --is-ancestor 0be28282ad1c3c748d9b06ab69a3f926dfbb89a2 "$GITHUB_SHA"
test "$(git hash-object research/lcrm01/mg05_native_only_preregistration.json)" = 42a9af5297177322b6613d7b6abf8afb53929c0d
test "$(git hash-object research/lcrm01/mg05_wingless_go_bridge.go)" = a3048550e7ddcf34498515eda8a9c9ab1ed2e3a4
test "$(git hash-object research/lcrm01/mg05_native_only_original_world.py)" = 8deef8ee14f7caaf4aa8cef53ff96bdd82069bf9
test "$(git hash-object research/lcrm01/mg05_compare.py)" = f103da405521809e632b41a33f363e1e99a715a1
test "$(git hash-object research/lcrm01/mg04_public_effect_native_agency.py)" = 2866af2978fa37702bc58ffa59eab5db37a262d9
test "$(git hash-object research/lcrm01/mg04_visible_effect_native_agency_prereg.json)" = 95a8a6fcd03ad790264439d0b8057c4eeab218b9
echo MG05_PROSPECTIVE_FROZEN_PARENT_AND_ORIGINAL_SOURCE_PASS

mkdir -p "$RUNNER_TEMP/mg05/minigrid" "$RUNNER_TEMP/mg05/wingless" "$RUNNER_TEMP/mg05/ygg" "$RUNNER_TEMP/mg05/collector"
python -m pip install 'pip==24.0' 'setuptools==69.5.1' 'wheel==0.43.0'
python -m pip install 'numpy==1.26.4' 'gymnasium==1.1.1' 'pygame-ce==2.5.3'

git init -q "$RUNNER_TEMP/mg05/minigrid"
git -C "$RUNNER_TEMP/mg05/minigrid" remote add origin https://github.com/Farama-Foundation/Minigrid.git
git -C "$RUNNER_TEMP/mg05/minigrid" fetch --no-tags --depth 1 origin 7f5853792ea7f04f75614661006d87fcf949f26d
git -C "$RUNNER_TEMP/mg05/minigrid" checkout --detach -q 7f5853792ea7f04f75614661006d87fcf949f26d
test "$(git -C "$RUNNER_TEMP/mg05/minigrid" hash-object minigrid/envs/doorkey.py)" = df5b29ef063be34e6d83b8b478e092c6e3e01512
python -m pip install --no-deps -e "$RUNNER_TEMP/mg05/minigrid"
echo MG05_AUTHENTIC_ORIGINAL_FARAMA_PUBLIC_SOURCE_PASS

git init -q "$RUNNER_TEMP/mg05/wingless"
git -C "$RUNNER_TEMP/mg05/wingless" remote add origin https://github.com/spoonman136668-ai/Wingless.git
git -C "$RUNNER_TEMP/mg05/wingless" fetch --no-tags --depth 1 origin d47291dc547fe3a23cc5f65df259b1dcf169fb2a
git -C "$RUNNER_TEMP/mg05/wingless" checkout --detach -q d47291dc547fe3a23cc5f65df259b1dcf169fb2a
test "$(git -C "$RUNNER_TEMP/mg05/wingless" hash-object research/native/itd02/dk8/explorer.go)" = 621d0d8b5bea7093c512903407a4a4bb812f4656
test "$(git -C "$RUNNER_TEMP/mg05/wingless" hash-object research/native/itd02/dk7/public_policy.go)" = b61ae9118dc1dae521f84ec44c72c891ce84df8c
test "$(git -C "$RUNNER_TEMP/mg05/wingless" hash-object research/native/itd02/r8/online_beliefs.go)" = 6857ecbef2d63f459a432a5d68c7edda2b5347c4
(cd "$RUNNER_TEMP/mg05/wingless" && go test -count=1 ./research/native/itd02/dk7 ./research/native/itd02/dk8 && go build -trimpath -o "$RUNNER_TEMP/mg05/native-dk8u-bridge" "$GITHUB_WORKSPACE/research/lcrm01/mg05_wingless_go_bridge.go")
echo MG05_WINGLESS_NEW_GO_NATIVE_ACTION_BRIDGE_PASS

git init -q "$RUNNER_TEMP/mg05/ygg"
git -C "$RUNNER_TEMP/mg05/ygg" remote add origin https://github.com/spoonman136668-ai/Yggdrasil.git
git -C "$RUNNER_TEMP/mg05/ygg" fetch --no-tags --depth 1 origin b27372e6c670166749dc3dc41ab6cfe9b263292f
git -C "$RUNNER_TEMP/mg05/ygg" checkout --detach -q b27372e6c670166749dc3dc41ab6cfe9b263292f
test "$(git -C "$RUNNER_TEMP/mg05/ygg" hash-object research/native/itd02/r13/explore_choice.py)" = 51c421fbd34b5e88e02bf89acab0de7b11eee1c9
test "$(git -C "$RUNNER_TEMP/mg05/ygg" hash-object research/native/itd02/r10/public_adapter.py)" = 3917d36ce9f86a2c1b998a0a2f93fb27674a9205
test "$(git -C "$RUNNER_TEMP/mg05/ygg" hash-object research/native/itd02/r11/affordance_cells.py)" = 614c7dfb1b43f485009b70cb85e9b7b5119cafc2
test "$(git -C "$RUNNER_TEMP/mg05/ygg" hash-object research/native/itd02/r12/outcome_choice.py)" = 2d19b28d6d4db1988ae908fe91be1a27ce4c1907
echo MG05_YGG_ORIGINAL_CELLS_NEW_UNCERTAINTY_SOURCE_PASS

git init -q "$RUNNER_TEMP/mg05/collector"
git -C "$RUNNER_TEMP/mg05/collector" remote add origin https://github.com/spoonman136668-ai/Yggdrasil.git
git -C "$RUNNER_TEMP/mg05/collector" fetch --no-tags --depth 1 origin 9d18cd04e7264898a92e4e382da6fac4398ad584
git -C "$RUNNER_TEMP/mg05/collector" checkout --detach -q 9d18cd04e7264898a92e4e382da6fac4398ad584
test "$(git -C "$RUNNER_TEMP/mg05/collector" hash-object research/mass_r7c29/collect.py)" = 3e5c5ce30d15f3741b45a4900a8341bc339a85c9
test "$(git -C "$RUNNER_TEMP/mg05/collector" hash-object research/mass_r7c30/control.py)" = c3183c8b8e43ef0e3531df964c80f0370fbc4914
export MG03_COLLECTOR_ROOT="$RUNNER_TEMP/mg05/collector"
export PYTHONPATH="$RUNNER_TEMP/mg05/ygg:$GITHUB_WORKSPACE/research/lcrm01"
echo MG05_IDENTICAL_TRAIN_SOURCE_WITH_NO_LIVE_COLLECTOR_PASS

python -B research/lcrm01/mg05_native_only_original_world.py --wingless-dk8u-go "$RUNNER_TEMP/mg05/native-dk8u-bridge" --output "$RUNNER_TEMP/mg05/first.json" > "$RUNNER_TEMP/mg05/first.log" 2>&1 || {
 cat "$RUNNER_TEMP/mg05/first.log"; exit 1;
}
cat "$RUNNER_TEMP/mg05/first.log"
python -B research/lcrm01/mg05_native_only_original_world.py --wingless-dk8u-go "$RUNNER_TEMP/mg05/native-dk8u-bridge" --output "$RUNNER_TEMP/mg05/second.json" > "$RUNNER_TEMP/mg05/second.log" 2>&1 || {
 cat "$RUNNER_TEMP/mg05/second.log"; exit 1;
}
cat "$RUNNER_TEMP/mg05/second.log"
python -B research/lcrm01/mg05_compare.py --first "$RUNNER_TEMP/mg05/first.json" --second "$RUNNER_TEMP/mg05/second.json" --output "$RUNNER_TEMP/mg05/comparison.json"
test -z "$(git status --porcelain --untracked-files=all)"
echo MG05_AUTHENTIC_PUBLIC_NATIVE_ONLY_ACTIONS_NO_SCIENCE
