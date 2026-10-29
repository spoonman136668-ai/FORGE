#!/usr/bin/env bash
# Original Farama DoorKey, authenticated source-only temporal decisions; NO C29 live.
set -euo pipefail
cd "$GITHUB_WORKSPACE"
export PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 PIP_DISABLE_PIP_VERSION_CHECK=1
git merge-base --is-ancestor 3ff11059a64041e8cfc1dce2d34c43a046a0f64d "$GITHUB_SHA"
git merge-base --is-ancestor fc57ff2af15ed9fe8f5ca69d532253973f0052c9 "$GITHUB_SHA"
git merge-base --is-ancestor d3357aa533a9669040974929467937ddcf40de96 "$GITHUB_SHA"
git merge-base --is-ancestor 94130f1905faaa0376607bbb8e91f98f524892bd "$GITHUB_SHA"
git merge-base --is-ancestor d93d5dba6702e55885e4ca2d48b43ad7863b40db "$GITHUB_SHA"
test "$(git hash-object research/lcrm01/mg06_original_doorkey_exploration.py)" = afadf926978721de852f5d49179562340908348e
test -z "$(git status --porcelain --untracked-files=all)"
echo MG07_FROZEN_PREREG_AND_OLD_SOURCE_PASS

mkdir -p "$RUNNER_TEMP/mg07/minigrid" "$RUNNER_TEMP/mg07/wingless" "$RUNNER_TEMP/mg07/yggdrasil" "$RUNNER_TEMP/mg07/collector"
python -m pip install 'pip==24.0' 'setuptools==69.5.1' 'wheel==0.43.0'
python -m pip install 'numpy==1.26.4' 'gymnasium==1.1.1' 'pygame-ce==2.5.3'

git init -q "$RUNNER_TEMP/mg07/minigrid"
git -C "$RUNNER_TEMP/mg07/minigrid" remote add origin https://github.com/Farama-Foundation/Minigrid.git
git -C "$RUNNER_TEMP/mg07/minigrid" fetch --no-tags --depth 1 origin 7f5853792ea7f04f75614661006d87fcf949f26d
git -C "$RUNNER_TEMP/mg07/minigrid" checkout --detach -q 7f5853792ea7f04f75614661006d87fcf949f26d
test "$(git -C "$RUNNER_TEMP/mg07/minigrid" hash-object minigrid/envs/doorkey.py)" = df5b29ef063be34e6d83b8b478e092c6e3e01512
test "$(git -C "$RUNNER_TEMP/mg07/minigrid" hash-object minigrid/wrappers.py)" = 1eb2da8fb612653c97f443ff6c7492ed3f1aaa80
test "$(git -C "$RUNNER_TEMP/mg07/minigrid" hash-object minigrid/minigrid_env.py)" = eb29e9a902de0715ab77ec981a2113576d7664fa
python -m pip install --no-deps -e "$RUNNER_TEMP/mg07/minigrid"
echo MG07_ORIGINAL_AUTHENTIC_FARAMA_DOORKEY_PIN_PASS

git init -q "$RUNNER_TEMP/mg07/wingless"
git -C "$RUNNER_TEMP/mg07/wingless" remote add origin https://github.com/spoonman136668-ai/Wingless.git
git -C "$RUNNER_TEMP/mg07/wingless" fetch --no-tags --depth 1 origin e8f6cf7bce6bf7580de9bb7ab861530d7fd1e220
git -C "$RUNNER_TEMP/mg07/wingless" checkout --detach -q e8f6cf7bce6bf7580de9bb7ab861530d7fd1e220
test "$(git -C "$RUNNER_TEMP/mg07/wingless" hash-object research/native/itd02/dk10/temporal_policy.go)" = 3575ca351467ffd6200d277acf72b0d78dd54a52
test "$(git -C "$RUNNER_TEMP/mg07/wingless" hash-object research/native/itd02/dk10bridge/main.go)" = ccc6a15eb970ef000a277cfac2dc6d2bf6389635
test "$(git -C "$RUNNER_TEMP/mg07/wingless" hash-object research/native/itd02/dk9/explore_policy.go)" = b2914104945ecc29ecc265dbc9ce03f78170dc7a
test "$(git -C "$RUNNER_TEMP/mg07/wingless" hash-object research/native/itd02/dk8/effect_policy.go)" = 01484d331e9df9035be045b31d0e015f1f8652e2
test "$(git -C "$RUNNER_TEMP/mg07/wingless" hash-object research/native/itd02/r8/online_beliefs.go)" = 6857ecbef2d63f459a432a5d68c7edda2b5347c4
(cd "$RUNNER_TEMP/mg07/wingless" && go test -count=1 ./research/native/itd02/dk10/... ./research/native/itd02/dk9/... && go build -trimpath -o "$RUNNER_TEMP/mg07/dk10-go" ./research/native/itd02/dk10bridge && go build -trimpath -o "$RUNNER_TEMP/mg07/dk9-go" ./research/native/itd02/dk9bridge)
echo MG07_WINGLESS_NATIVE_GO_NEW_AND_PARENT_SOURCE_EXACT

git init -q "$RUNNER_TEMP/mg07/yggdrasil"
git -C "$RUNNER_TEMP/mg07/yggdrasil" remote add origin https://github.com/spoonman136668-ai/Yggdrasil.git
git -C "$RUNNER_TEMP/mg07/yggdrasil" fetch --no-tags --depth 1 origin c09b674d7045daca98b7881fda2fe54120c8fdd6
git -C "$RUNNER_TEMP/mg07/yggdrasil" checkout --detach -q c09b674d7045daca98b7881fda2fe54120c8fdd6
test "$(git -C "$RUNNER_TEMP/mg07/yggdrasil" hash-object research/native/itd02/r14/temporal_cells.py)" = 8cacaad50e8d484f72da5067ff1f03c187877f27
test "$(git -C "$RUNNER_TEMP/mg07/yggdrasil" hash-object research/native/itd02/r13/explore_choice.py)" = 51c421fbd34b5e88e02bf89acab0de7b11eee1c9
test "$(git -C "$RUNNER_TEMP/mg07/yggdrasil" hash-object research/native/itd02/r10/public_adapter.py)" = 3917d36ce9f86a2c1b998a0a2f93fb27674a9205
test "$(git -C "$RUNNER_TEMP/mg07/yggdrasil" hash-object research/native/itd02/r11/affordance_cells.py)" = 614c7dfb1b43f485009b70cb85e9b7b5119cafc2
test "$(git -C "$RUNNER_TEMP/mg07/yggdrasil" hash-object research/native/itd02/r12/outcome_choice.py)" = 2d19b28d6d4db1988ae908fe91be1a27ce4c1907
echo MG07_YGGDRASIL_LOCAL_CELL_SOURCE_NEW_AND_PARENT_PIN_PASS

git init -q "$RUNNER_TEMP/mg07/collector"
git -C "$RUNNER_TEMP/mg07/collector" remote add origin https://github.com/spoonman136668-ai/Yggdrasil.git
git -C "$RUNNER_TEMP/mg07/collector" fetch --no-tags --depth 1 origin 9d18cd04e7264898a92e4e382da6fac4398ad584
git -C "$RUNNER_TEMP/mg07/collector" checkout --detach -q 9d18cd04e7264898a92e4e382da6fac4398ad584
test "$(git -C "$RUNNER_TEMP/mg07/collector" hash-object research/mass_r7c29/collect.py)" = 3e5c5ce30d15f3741b45a4900a8341bc339a85c9
test "$(git -C "$RUNNER_TEMP/mg07/collector" hash-object research/mass_r7c30/control.py)" = c3183c8b8e43ef0e3531df964c80f0370fbc4914
export MG03_COLLECTOR_ROOT="$RUNNER_TEMP/mg07/collector"
export PYTHONPATH="$RUNNER_TEMP/mg07/yggdrasil:$GITHUB_WORKSPACE/research/lcrm01"
echo MG07_CONVENTIONAL_C30_AND_FIT_ONLY_C29_ORIGINAL_SOURCE_PASS

python -B research/lcrm01/mg07_temporal_original_doorkey.py \
 --wingless-dk10 "$RUNNER_TEMP/mg07/dk10-go" \
 --wingless-dk9 "$RUNNER_TEMP/mg07/dk9-go" \
 --output "$RUNNER_TEMP/mg07/first.json" > "$RUNNER_TEMP/mg07/first.log" 2>&1 || {
 cat "$RUNNER_TEMP/mg07/first.log"; exit 1;
}
cat "$RUNNER_TEMP/mg07/first.log"
python -B research/lcrm01/mg07_temporal_original_doorkey.py \
 --wingless-dk10 "$RUNNER_TEMP/mg07/dk10-go" \
 --wingless-dk9 "$RUNNER_TEMP/mg07/dk9-go" \
 --output "$RUNNER_TEMP/mg07/second.json" > "$RUNNER_TEMP/mg07/second.log" 2>&1 || {
 cat "$RUNNER_TEMP/mg07/second.log"; exit 1;
}
cat "$RUNNER_TEMP/mg07/second.log"
python -B research/lcrm01/mg07_compare.py \
 --first "$RUNNER_TEMP/mg07/first.json" \
 --second "$RUNNER_TEMP/mg07/second.json" \
 --output "$RUNNER_TEMP/mg07/comparison.json"
test -z "$(git status --porcelain --untracked-files=all)"
test -z "$(git -C "$RUNNER_TEMP/mg07/minigrid" status --porcelain --untracked-files=no)"
test -z "$(git -C "$RUNNER_TEMP/mg07/wingless" status --porcelain --untracked-files=no)"
test -z "$(git -C "$RUNNER_TEMP/mg07/yggdrasil" status --porcelain --untracked-files=no)"
test -z "$(git -C "$RUNNER_TEMP/mg07/collector" status --porcelain --untracked-files=no)"
echo MG07_AUTHENTIC_ORIGINAL_DOORKEY_SELECTED_PUBLIC_TEMPORAL_GATE_COMPLETED_NOT_SCIENCE
