#!/usr/bin/env bash
# MG04 exact original DoorKey, three independent agents and same 1664 FIT.
set -euo pipefail
cd "$GITHUB_WORKSPACE"
export PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 PIP_DISABLE_PIP_VERSION_CHECK=1
git merge-base --is-ancestor 105f953b8536bde78688f0b618f75c9cd51b4696 "$GITHUB_SHA"
git merge-base --is-ancestor 25009e6f9702d8293f012615510b0f9cf453864f "$GITHUB_SHA"
git merge-base --is-ancestor dee3f57d93a5f304355f3622d61fe784da74fe7d "$GITHUB_SHA"
git merge-base --is-ancestor a7133f77ead17100087af6d0edbdcd2e927cc324 "$GITHUB_SHA"
test "$(git hash-object research/lcrm01/mg03_equal_public_doorkey_live.py)" = "$(git show 105f953b8536bde78688f0b618f75c9cd51b4696:research/lcrm01/mg03_equal_public_doorkey_live.py | git hash-object --stdin)"
echo MG04_PREREG_PARENT_ORIGINAL_SOURCE_FROZEN_PASS

mkdir -p "$RUNNER_TEMP/mg04/minigrid" "$RUNNER_TEMP/mg04/wingless" "$RUNNER_TEMP/mg04/ygg-r12" "$RUNNER_TEMP/mg04/collector"
python -m pip install 'pip==24.0' 'setuptools==69.5.1' 'wheel==0.43.0'
python -m pip install 'numpy==1.26.4' 'gymnasium==1.1.1' 'pygame-ce==2.5.3'

git init -q "$RUNNER_TEMP/mg04/minigrid"
git -C "$RUNNER_TEMP/mg04/minigrid" remote add origin https://github.com/Farama-Foundation/Minigrid.git
git -C "$RUNNER_TEMP/mg04/minigrid" fetch --no-tags --depth 1 origin 7f5853792ea7f04f75614661006d87fcf949f26d
git -C "$RUNNER_TEMP/mg04/minigrid" checkout --detach -q 7f5853792ea7f04f75614661006d87fcf949f26d
test "$(git -C "$RUNNER_TEMP/mg04/minigrid" hash-object minigrid/envs/doorkey.py)" = df5b29ef063be34e6d83b8b478e092c6e3e01512
test "$(git -C "$RUNNER_TEMP/mg04/minigrid" hash-object minigrid/wrappers.py)" = 1eb2da8fb612653c97f443ff6c7492ed3f1aaa80
python -m pip install --no-deps -e "$RUNNER_TEMP/mg04/minigrid"
echo MG04_AUTHENTIC_ORIGINAL_FARAMA_DOORKEY_PIN_PASS

git init -q "$RUNNER_TEMP/mg04/wingless"
git -C "$RUNNER_TEMP/mg04/wingless" remote add origin https://github.com/spoonman136668-ai/Wingless.git
git -C "$RUNNER_TEMP/mg04/wingless" fetch --no-tags --depth 1 origin 40fbec49fda33a04fea640535a8aaeaa29493cc7
git -C "$RUNNER_TEMP/mg04/wingless" checkout --detach -q 40fbec49fda33a04fea640535a8aaeaa29493cc7
test "$(git -C "$RUNNER_TEMP/mg04/wingless" hash-object research/native/itd02/dk7/public_policy.go)" = b61ae9118dc1dae521f84ec44c72c891ce84df8c
test "$(git -C "$RUNNER_TEMP/mg04/wingless" hash-object research/native/itd02/r8/online_beliefs.go)" = 6857ecbef2d63f459a432a5d68c7edda2b5347c4
(cd "$RUNNER_TEMP/mg04/wingless" && go test -count=1 ./research/native/itd02/dk8/... && go build -trimpath -o "$RUNNER_TEMP/mg04/dk8-native-go" ./research/native/itd02/dk8bridge)
echo MG04_GO_NEW_OPT_IN_NATIVE_EFFECTS_SOURCE_PASS

git init -q "$RUNNER_TEMP/mg04/ygg-r12"
git -C "$RUNNER_TEMP/mg04/ygg-r12" remote add origin https://github.com/spoonman136668-ai/Yggdrasil.git
git -C "$RUNNER_TEMP/mg04/ygg-r12" fetch --no-tags --depth 1 origin 6e2d4a219b1fb62e0124ba053b65b7e3fdd46546
git -C "$RUNNER_TEMP/mg04/ygg-r12" checkout --detach -q 6e2d4a219b1fb62e0124ba053b65b7e3fdd46546
test "$(git -C "$RUNNER_TEMP/mg04/ygg-r12" hash-object research/native/itd02/r10/public_adapter.py)" = 3917d36ce9f86a2c1b998a0a2f93fb27674a9205
test "$(git -C "$RUNNER_TEMP/mg04/ygg-r12" hash-object research/native/itd02/r11/affordance_cells.py)" = 614c7dfb1b43f485009b70cb85e9b7b5119cafc2
test "$(git -C "$RUNNER_TEMP/mg04/ygg-r12" hash-object research/native/itd02/r12/outcome_choice.py)" = 2d19b28d6d4db1988ae908fe91be1a27ce4c1907

git init -q "$RUNNER_TEMP/mg04/collector"
git -C "$RUNNER_TEMP/mg04/collector" remote add origin https://github.com/spoonman136668-ai/Yggdrasil.git
git -C "$RUNNER_TEMP/mg04/collector" fetch --no-tags --depth 1 origin 9d18cd04e7264898a92e4e382da6fac4398ad584
git -C "$RUNNER_TEMP/mg04/collector" checkout --detach -q 9d18cd04e7264898a92e4e382da6fac4398ad584
test "$(git -C "$RUNNER_TEMP/mg04/collector" hash-object research/mass_r7c29/collect.py)" = 3e5c5ce30d15f3741b45a4900a8341bc339a85c9
test "$(git -C "$RUNNER_TEMP/mg04/collector" hash-object research/mass_r7c30/control.py)" = c3183c8b8e43ef0e3531df964c80f0370fbc4914
export MG03_COLLECTOR_ROOT="$RUNNER_TEMP/mg04/collector"
export PYTHONPATH="$RUNNER_TEMP/mg04/ygg-r12:$GITHUB_WORKSPACE/research/lcrm01"
echo MG04_ORIGINAL_R12_AND_INDEPENDENT_CONVENTIONAL_PUBLIC_SOURCE_PIN_PASS

python -B research/lcrm01/mg04_public_effect_native_agency.py \
 --wingless-dk8-go "$RUNNER_TEMP/mg04/dk8-native-go" \
 --output "$RUNNER_TEMP/mg04/first.json" > "$RUNNER_TEMP/mg04/first.log" 2>&1 || {
 cat "$RUNNER_TEMP/mg04/first.log"; exit 1;
}
cat "$RUNNER_TEMP/mg04/first.log"
python -B research/lcrm01/mg04_public_effect_native_agency.py \
 --wingless-dk8-go "$RUNNER_TEMP/mg04/dk8-native-go" \
 --output "$RUNNER_TEMP/mg04/second.json" > "$RUNNER_TEMP/mg04/second.log" 2>&1 || {
 cat "$RUNNER_TEMP/mg04/second.log"; exit 1;
}
cat "$RUNNER_TEMP/mg04/second.log"
python -B research/lcrm01/mg04_compare.py \
 --first "$RUNNER_TEMP/mg04/first.json" \
 --second "$RUNNER_TEMP/mg04/second.json" \
 --output "$RUNNER_TEMP/mg04/comparison.json"
test -z "$(git status --porcelain --untracked-files=all)"
test -z "$(git -C "$RUNNER_TEMP/mg04/wingless" status --porcelain --untracked-files=no)"
test -z "$(git -C "$RUNNER_TEMP/mg04/ygg-r12" status --porcelain --untracked-files=no)"
test -z "$(git -C "$RUNNER_TEMP/mg04/minigrid" status --porcelain --untracked-files=no)"
test -z "$(git -C "$RUNNER_TEMP/mg04/collector" status --porcelain --untracked-files=no)"
echo MG04_AUTHENTIC_ORIGINAL_DOORKEY_ENGINEERING_CUSTODY_RECORDED_NOT_SCIENCE
