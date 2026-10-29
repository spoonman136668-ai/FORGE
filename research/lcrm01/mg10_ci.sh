#!/usr/bin/env bash
# Source-only MG10, original Farama and independent Go/Ygg/conventional.
set -euo pipefail
cd "$GITHUB_WORKSPACE"
export PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 PIP_DISABLE_PIP_VERSION_CHECK=1
git merge-base --is-ancestor 12d34b631b8c5b865d61d8327695c55f72030109 "$GITHUB_SHA"
git merge-base --is-ancestor f241571790298e1460c6fd4e2db5bc98ae7fcbe7 "$GITHUB_SHA"
git merge-base --is-ancestor 5393057e34af576f49431c80a673497471da7e0d "$GITHUB_SHA"
git merge-base --is-ancestor a667d381734ce6263a12848146881f6c95d23991 "$GITHUB_SHA"
git merge-base --is-ancestor cfa0d1073c7893d51d3735b1896ca21c3984073e "$GITHUB_SHA"
test "$(git hash-object research/lcrm01/mg09_original_orientation_retention.py)" = "$(git show 12d34b631b8c5b865d61d8327695c55f72030109:research/lcrm01/mg09_original_orientation_retention.py | git hash-object --stdin)"
test "$(git hash-object research/lcrm01/mg04_public_effect_native_agency.py)" = 2866af2978fa37702bc58ffa59eab5db37a262d9
test -z "$(git status --porcelain --untracked-files=all)"
echo MG10_PREREG_SOURCE_AND_OLD_GATES_FROZEN_PASS
mkdir -p "$RUNNER_TEMP/mg10/farama" "$RUNNER_TEMP/mg10/wingless" "$RUNNER_TEMP/mg10/yggdrasil" "$RUNNER_TEMP/mg10/collector"
python -m pip install 'pip==24.0' 'setuptools==69.5.1' 'wheel==0.43.0'
python -m pip install 'numpy==1.26.4' 'gymnasium==1.1.1' 'pygame-ce==2.5.3'

git init -q "$RUNNER_TEMP/mg10/farama"
git -C "$RUNNER_TEMP/mg10/farama" remote add origin https://github.com/Farama-Foundation/Minigrid.git
git -C "$RUNNER_TEMP/mg10/farama" fetch --no-tags --depth 1 origin 7f5853792ea7f04f75614661006d87fcf949f26d
git -C "$RUNNER_TEMP/mg10/farama" checkout --detach -q 7f5853792ea7f04f75614661006d87fcf949f26d
test "$(git -C "$RUNNER_TEMP/mg10/farama" hash-object minigrid/envs/doorkey.py)" = df5b29ef063be34e6d83b8b478e092c6e3e01512
test "$(git -C "$RUNNER_TEMP/mg10/farama" hash-object minigrid/wrappers.py)" = 1eb2da8fb612653c97f443ff6c7492ed3f1aaa80
python -m pip install --no-deps -e "$RUNNER_TEMP/mg10/farama"
echo MG10_AUTHENTIC_ORIGINAL_FARAMA_SOURCE_PINS_PASS

git init -q "$RUNNER_TEMP/mg10/wingless"
git -C "$RUNNER_TEMP/mg10/wingless" remote add origin https://github.com/spoonman136668-ai/Wingless.git
git -C "$RUNNER_TEMP/mg10/wingless" fetch --no-tags --depth 1 origin 5b5cda4346e278f46874d2f9264b22a5cf5a01ba
git -C "$RUNNER_TEMP/mg10/wingless" checkout --detach -q 5b5cda4346e278f46874d2f9264b22a5cf5a01ba
test "$(git -C "$RUNNER_TEMP/mg10/wingless" hash-object research/native/itd02/dk11/continuity.go)" = 228027db110c3924aebf63420ff2caed47fe8c73
test "$(git -C "$RUNNER_TEMP/mg10/wingless" hash-object research/native/itd02/dk11bridge/main.go)" = 2b52a699859c12db2be51698ce3567dfa98413eb
test "$(git -C "$RUNNER_TEMP/mg10/wingless" hash-object research/native/itd02/dk10/temporal_policy.go)" = 3575ca351467ffd6200d277acf72b0d78dd54a52
test "$(git -C "$RUNNER_TEMP/mg10/wingless" hash-object research/native/itd02/r8/online_beliefs.go)" = 6857ecbef2d63f459a432a5d68c7edda2b5347c4
(cd "$RUNNER_TEMP/mg10/wingless" && go test -count=1 ./research/native/itd02/dk11/... ./research/native/itd02/dk10/... && go build -trimpath -o "$RUNNER_TEMP/mg10/dk11-go" ./research/native/itd02/dk11bridge)
echo MG10_GO_NATIVE_DK11_NO_STAGE_SOURCE_QUALIFIED

git init -q "$RUNNER_TEMP/mg10/yggdrasil"
git -C "$RUNNER_TEMP/mg10/yggdrasil" remote add origin https://github.com/spoonman136668-ai/Yggdrasil.git
git -C "$RUNNER_TEMP/mg10/yggdrasil" fetch --no-tags --depth 1 origin 630dde83f45d845488d59a36136d6c026e10880b
git -C "$RUNNER_TEMP/mg10/yggdrasil" checkout --detach -q 630dde83f45d845488d59a36136d6c026e10880b
test "$(git -C "$RUNNER_TEMP/mg10/yggdrasil" hash-object research/native/itd02/r15/continuity_cells.py)" = 6b31f4b0c301564b2793bef8a296a4e722825f01
test "$(git -C "$RUNNER_TEMP/mg10/yggdrasil" hash-object research/native/itd02/r14/temporal_cells.py)" = 8cacaad50e8d484f72da5067ff1f03c187877f27
test "$(git -C "$RUNNER_TEMP/mg10/yggdrasil" hash-object research/native/itd02/r11/affordance_cells.py)" = 614c7dfb1b43f485009b70cb85e9b7b5119cafc2
test "$(git -C "$RUNNER_TEMP/mg10/yggdrasil" hash-object research/native/itd02/r10/public_adapter.py)" = 3917d36ce9f86a2c1b998a0a2f93fb27674a9205
echo MG10_YGG_NATIVE_R15_LOCAL_CELL_SOURCE_QUALIFIED

git init -q "$RUNNER_TEMP/mg10/collector"
git -C "$RUNNER_TEMP/mg10/collector" remote add origin https://github.com/spoonman136668-ai/Yggdrasil.git
git -C "$RUNNER_TEMP/mg10/collector" fetch --no-tags --depth 1 origin 9d18cd04e7264898a92e4e382da6fac4398ad584
git -C "$RUNNER_TEMP/mg10/collector" checkout --detach -q 9d18cd04e7264898a92e4e382da6fac4398ad584
test "$(git -C "$RUNNER_TEMP/mg10/collector" hash-object research/mass_r7c29/collect.py)" = 3e5c5ce30d15f3741b45a4900a8341bc339a85c9
test "$(git -C "$RUNNER_TEMP/mg10/collector" hash-object research/mass_r7c30/control.py)" = c3183c8b8e43ef0e3531df964c80f0370fbc4914
export MG03_COLLECTOR_ROOT="$RUNNER_TEMP/mg10/collector"
export PYTHONPATH="$RUNNER_TEMP/mg10/yggdrasil:$GITHUB_WORKSPACE/research/lcrm01"
echo MG10_TRUE_INDEPENDENT_CONVENTIONAL_SOURCE_PINS_PASS

python -B research/lcrm01/mg10_stage_free_original_doorkey.py \
 --wingless-dk11 "$RUNNER_TEMP/mg10/dk11-go" \
 --output "$RUNNER_TEMP/mg10/first.json" > "$RUNNER_TEMP/mg10/first.log" 2>&1 || {
 cat "$RUNNER_TEMP/mg10/first.log"; exit 1;
}
cat "$RUNNER_TEMP/mg10/first.log"
python -B research/lcrm01/mg10_stage_free_original_doorkey.py \
 --wingless-dk11 "$RUNNER_TEMP/mg10/dk11-go" \
 --output "$RUNNER_TEMP/mg10/second.json" > "$RUNNER_TEMP/mg10/second.log" 2>&1 || {
 cat "$RUNNER_TEMP/mg10/second.log"; exit 1;
}
cat "$RUNNER_TEMP/mg10/second.log"
python -B research/lcrm01/mg10_compare.py \
 --first "$RUNNER_TEMP/mg10/first.json" \
 --second "$RUNNER_TEMP/mg10/second.json" \
 --output "$RUNNER_TEMP/mg10/comparison.json"
test -z "$(git status --porcelain --untracked-files=all)"
echo MG10_STAGE_FREE_NATIVE_AND_CONVENTIONAL_REAL_ORIGINAL_SOURCE_COMPLETED_NOT_SCIENCE
