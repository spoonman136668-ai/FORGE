#!/usr/bin/env bash
# MG16 original Farama source development; same public policy input, no live C29.
set -euo pipefail
cd "$GITHUB_WORKSPACE"
export PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 PIP_DISABLE_PIP_VERSION_CHECK=1

git merge-base --is-ancestor f3c4b9d37a5a1c48966686955dabe8fcce757275 "$GITHUB_SHA"
git merge-base --is-ancestor bf60979058104f01e6e5a8428d4b81277d8ee031 "$GITHUB_SHA"
test "$(git hash-object research/lcrm01/mg16_original_credit_run_prereg.json)" = 2904ceec237a966a162c5bc47fb9de35a1b9d6b7
test "$(git hash-object research/lcrm01/mg15_go_bridge.go)" = ae07ee16827828f1f022359f3709ee1ac2a0441d
test "$(git hash-object research/lcrm01/mg16_original_state_credit.py)" = e02f4bf6594e5745ac8f9eebc753a40c53d5e11f
test "$(git hash-object research/lcrm01/mg16_compare.py)" = 1e1748f20db249aab41fad3cefe7a3b6aaa0db72
test "$(git hash-object research/lcrm01/mg16_go_bridge.go)" = 444b2c5b5835a697d2228205bf75f616321a691f
test "$(git hash-object research/lcrm01/mg15_original_mission.py)" = d79de5e517ec4a555a2c92af84cd962a0f4a3443
test -z "$(git status --porcelain --untracked-files=all)"
echo MG16_BEFORE_SOURCE_FROZEN_PREREG_AND_CODE_PINS_PASS

mkdir -p "$RUNNER_TEMP/mg16/minigrid" "$RUNNER_TEMP/mg16/wingless" "$RUNNER_TEMP/mg16/wingless-new" "$RUNNER_TEMP/mg16/yggdrasil" "$RUNNER_TEMP/mg16/collector"
python -m pip install 'pip==24.0' 'setuptools==69.5.1' 'wheel==0.43.0'
python -m pip install 'numpy==1.26.4' 'gymnasium==1.1.1' 'pygame-ce==2.5.3'

git init -q "$RUNNER_TEMP/mg16/minigrid"
git -C "$RUNNER_TEMP/mg16/minigrid" remote add origin https://github.com/Farama-Foundation/Minigrid.git
git -C "$RUNNER_TEMP/mg16/minigrid" fetch --no-tags --depth 1 origin 7f5853792ea7f04f75614661006d87fcf949f26d
git -C "$RUNNER_TEMP/mg16/minigrid" checkout --detach -q 7f5853792ea7f04f75614661006d87fcf949f26d
test "$(git -C "$RUNNER_TEMP/mg16/minigrid" hash-object minigrid/envs/doorkey.py)" = df5b29ef063be34e6d83b8b478e092c6e3e01512
test "$(git -C "$RUNNER_TEMP/mg16/minigrid" hash-object minigrid/envs/empty.py)" = 8810bb0fa156d18475022edd8859b135ef745a5f
test "$(git -C "$RUNNER_TEMP/mg16/minigrid" hash-object minigrid/minigrid_env.py)" = eb29e9a902de0715ab77ec981a2113576d7664fa
python -m pip install --no-deps -e "$RUNNER_TEMP/mg16/minigrid"
echo MG16_AUTHENTIC_ORIGINAL_FARAMA_SOURCE_PASS

git init -q "$RUNNER_TEMP/mg16/wingless"
git -C "$RUNNER_TEMP/mg16/wingless" remote add origin https://github.com/spoonman136668-ai/Wingless.git
git -C "$RUNNER_TEMP/mg16/wingless" fetch --no-tags --depth 1 origin 4e7f76573a0a3d3978e85f98b256659f71bc44c4
git -C "$RUNNER_TEMP/mg16/wingless" checkout --detach -q 4e7f76573a0a3d3978e85f98b256659f71bc44c4
test "$(git -C "$RUNNER_TEMP/mg16/wingless" hash-object research/native/itd02/dk14/mission.go)" = 229600d22c36c3fc8a8abdf2eca555f9fe43ba1f
test "$(git -C "$RUNNER_TEMP/mg16/wingless" hash-object research/native/itd02/dk10/temporal_policy.go)" = 3575ca351467ffd6200d277acf72b0d78dd54a52
test "$(git -C "$RUNNER_TEMP/mg16/wingless" hash-object research/native/itd02/r8/online_beliefs.go)" = 6857ecbef2d63f459a432a5d68c7edda2b5347c4
(cd "$RUNNER_TEMP/mg16/wingless" &&
  go test -count=1 ./research/native/itd02/dk14/... ./research/native/itd02/dk10/... &&
  go build -trimpath -o "$RUNNER_TEMP/mg16/native-dk14-source" "$GITHUB_WORKSPACE/research/lcrm01/mg15_go_bridge.go")
echo MG16_INDEPENDENT_GO_NATIVE_NO_OBJECTIVE_SOURCE_PASS
git init -q "$RUNNER_TEMP/mg16/wingless-new"
git -C "$RUNNER_TEMP/mg16/wingless-new" remote add origin https://github.com/spoonman136668-ai/Wingless.git
git -C "$RUNNER_TEMP/mg16/wingless-new" fetch --no-tags --depth 1 origin e2ff8bcd4b9e84f4284e07a44034777238abcc9e
git -C "$RUNNER_TEMP/mg16/wingless-new" checkout --detach -q e2ff8bcd4b9e84f4284e07a44034777238abcc9e
test "$(git -C "$RUNNER_TEMP/mg16/wingless-new" hash-object research/native/itd02/dk16/state_credit.go)" = 4b1c7ce2ceb0f33580a014c33657f9f7a84e5d7b
test "$(git -C "$RUNNER_TEMP/mg16/wingless-new" hash-object research/native/itd02/dk16/checkpoint.go)" = 30f758ff6ab120228e1c2fe7be05dd46e04e7a79
test "$(git -C "$RUNNER_TEMP/mg16/wingless-new" hash-object research/native/itd02/dk14/mission.go)" = 229600d22c36c3fc8a8abdf2eca555f9fe43ba1f
(cd "$RUNNER_TEMP/mg16/wingless-new" &&
 go test -count=1 ./research/native/itd02/dk16/... &&
 go build -trimpath -o "$RUNNER_TEMP/mg16/native-dk16-source" "$GITHUB_WORKSPACE/research/lcrm01/mg16_go_bridge.go")
echo MG16_NATIVE_DK16_SOURCE_QUALIFIED


git init -q "$RUNNER_TEMP/mg16/yggdrasil"
git -C "$RUNNER_TEMP/mg16/yggdrasil" remote add origin https://github.com/spoonman136668-ai/Yggdrasil.git
git -C "$RUNNER_TEMP/mg16/yggdrasil" fetch --no-tags --depth 1 origin a9942978f92e762e404fe50ce29445ea4639b4c2
git -C "$RUNNER_TEMP/mg16/yggdrasil" checkout --detach -q a9942978f92e762e404fe50ce29445ea4639b4c2
test "$(git -C "$RUNNER_TEMP/mg16/yggdrasil" hash-object research/native/itd02/r18/mission_cells.py)" = 531b4f258408eb38f38794f03a192aacdad42315
test "$(git -C "$RUNNER_TEMP/mg16/yggdrasil" hash-object research/native/itd02/r20/state_credit_cells.py)" = b81af09e879ddab30955bd5debc2a89ce5266ae3
test "$(git -C "$RUNNER_TEMP/mg16/yggdrasil" hash-object research/native/itd02/r14/temporal_cells.py)" = 8cacaad50e8d484f72da5067ff1f03c187877f27
test "$(git -C "$RUNNER_TEMP/mg16/yggdrasil" hash-object research/native/itd02/r11/affordance_cells.py)" = 614c7dfb1b43f485009b70cb85e9b7b5119cafc2
echo MG16_INDEPENDENT_YGG_NATIVE_LOCAL_CELL_SOURCE_PASS

git init -q "$RUNNER_TEMP/mg16/collector"
git -C "$RUNNER_TEMP/mg16/collector" remote add origin https://github.com/spoonman136668-ai/Yggdrasil.git
git -C "$RUNNER_TEMP/mg16/collector" fetch --no-tags --depth 1 origin 9d18cd04e7264898a92e4e382da6fac4398ad584
git -C "$RUNNER_TEMP/mg16/collector" checkout --detach -q 9d18cd04e7264898a92e4e382da6fac4398ad584
test "$(git -C "$RUNNER_TEMP/mg16/collector" hash-object research/mass_r7c29/collect.py)" = 3e5c5ce30d15f3741b45a4900a8341bc339a85c9
test "$(git -C "$RUNNER_TEMP/mg16/collector" hash-object research/mass_r7c30/control.py)" = c3183c8b8e43ef0e3531df964c80f0370fbc4914
export MG03_COLLECTOR_ROOT="$RUNNER_TEMP/mg16/collector"
export PYTHONPATH="$RUNNER_TEMP/mg16/yggdrasil:$GITHUB_WORKSPACE/research/lcrm01"
echo MG16_FIT_ONLY_C29_1664_AND_EXPLICIT_UNASSISTED_CONVENTIONAL_PASS

python -B research/lcrm01/mg16_original_state_credit.py \
  --native-go-dk11 "$RUNNER_TEMP/mg16/native-dk16-source" \
  --native-go-parent "$RUNNER_TEMP/mg16/native-dk14-source" \
  --output "$RUNNER_TEMP/mg16/first.json" > "$RUNNER_TEMP/mg16/first.log" 2>&1 || {
  cat "$RUNNER_TEMP/mg16/first.log"; exit 1;
}
cat "$RUNNER_TEMP/mg16/first.log"
python -B research/lcrm01/mg16_original_state_credit.py \
  --native-go-dk11 "$RUNNER_TEMP/mg16/native-dk16-source" \
  --native-go-parent "$RUNNER_TEMP/mg16/native-dk14-source" \
  --output "$RUNNER_TEMP/mg16/second.json" > "$RUNNER_TEMP/mg16/second.log" 2>&1 || {
  cat "$RUNNER_TEMP/mg16/second.log"; exit 1;
}
cat "$RUNNER_TEMP/mg16/second.log"
python -B research/lcrm01/mg16_compare.py \
  --first "$RUNNER_TEMP/mg16/first.json" \
  --second "$RUNNER_TEMP/mg16/second.json" \
  --output "$RUNNER_TEMP/mg16/comparison.json"
test -z "$(git status --porcelain --untracked-files=all)"
echo MG16_ORIGINAL_SOURCE_EQUAL_RAW_PUBLIC_QUALIFIED__NOT_SCIENCE
