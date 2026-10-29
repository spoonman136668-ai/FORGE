#!/usr/bin/env bash
# MG15 original Farama source development; same public policy input, no live C29.
set -euo pipefail
cd "$GITHUB_WORKSPACE"
export PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 PIP_DISABLE_PIP_VERSION_CHECK=1

git merge-base --is-ancestor f3c4b9d37a5a1c48966686955dabe8fcce757275 "$GITHUB_SHA"
git merge-base --is-ancestor 3d1b55bc593bda9f0b804ed383603b04897cfd4a "$GITHUB_SHA"
test "$(git hash-object research/lcrm01/mg15_original_mission_run_prereg.json)" = 22c8456c6f2592ff834061f6c70be1c394083941
test "$(git hash-object research/lcrm01/mg15_go_bridge.go)" = 1f1b8d27f0bcb0ab8dfa9d6052ae8fb7502a4cb4
test "$(git hash-object research/lcrm01/mg15_original_mission.py)" = d79de5e517ec4a555a2c92af84cd962a0f4a3443
test "$(git hash-object research/lcrm01/mg15_compare.py)" = 6f59df54e8fcaef0b9639c375515126a1b769bc5
test -z "$(git status --porcelain --untracked-files=all)"
echo MG15_BEFORE_SOURCE_FROZEN_PREREG_AND_CODE_PINS_PASS

mkdir -p "$RUNNER_TEMP/mg15/minigrid" "$RUNNER_TEMP/mg15/wingless" "$RUNNER_TEMP/mg15/yggdrasil" "$RUNNER_TEMP/mg15/collector"
python -m pip install 'pip==24.0' 'setuptools==69.5.1' 'wheel==0.43.0'
python -m pip install 'numpy==1.26.4' 'gymnasium==1.1.1' 'pygame-ce==2.5.3'

git init -q "$RUNNER_TEMP/mg15/minigrid"
git -C "$RUNNER_TEMP/mg15/minigrid" remote add origin https://github.com/Farama-Foundation/Minigrid.git
git -C "$RUNNER_TEMP/mg15/minigrid" fetch --no-tags --depth 1 origin 7f5853792ea7f04f75614661006d87fcf949f26d
git -C "$RUNNER_TEMP/mg15/minigrid" checkout --detach -q 7f5853792ea7f04f75614661006d87fcf949f26d
test "$(git -C "$RUNNER_TEMP/mg15/minigrid" hash-object minigrid/envs/doorkey.py)" = df5b29ef063be34e6d83b8b478e092c6e3e01512
test "$(git -C "$RUNNER_TEMP/mg15/minigrid" hash-object minigrid/envs/empty.py)" = 8810bb0fa156d18475022edd8859b135ef745a5f
test "$(git -C "$RUNNER_TEMP/mg15/minigrid" hash-object minigrid/minigrid_env.py)" = eb29e9a902de0715ab77ec981a2113576d7664fa
python -m pip install --no-deps -e "$RUNNER_TEMP/mg15/minigrid"
echo MG15_AUTHENTIC_ORIGINAL_FARAMA_SOURCE_PASS

git init -q "$RUNNER_TEMP/mg15/wingless"
git -C "$RUNNER_TEMP/mg15/wingless" remote add origin https://github.com/spoonman136668-ai/Wingless.git
git -C "$RUNNER_TEMP/mg15/wingless" fetch --no-tags --depth 1 origin 4e7f76573a0a3d3978e85f98b256659f71bc44c4
git -C "$RUNNER_TEMP/mg15/wingless" checkout --detach -q 4e7f76573a0a3d3978e85f98b256659f71bc44c4
test "$(git -C "$RUNNER_TEMP/mg15/wingless" hash-object research/native/itd02/dk14/mission.go)" = 229600d22c36c3fc8a8abdf2eca555f9fe43ba1f
test "$(git -C "$RUNNER_TEMP/mg15/wingless" hash-object research/native/itd02/dk10/temporal_policy.go)" = 3575ca351467ffd6200d277acf72b0d78dd54a52
test "$(git -C "$RUNNER_TEMP/mg15/wingless" hash-object research/native/itd02/r8/online_beliefs.go)" = 6857ecbef2d63f459a432a5d68c7edda2b5347c4
(cd "$RUNNER_TEMP/mg15/wingless" &&
  go test -count=1 ./research/native/itd02/dk14/... ./research/native/itd02/dk10/... &&
  go build -trimpath -o "$RUNNER_TEMP/mg15/native-dk14-source" "$GITHUB_WORKSPACE/research/lcrm01/mg15_go_bridge.go")
echo MG15_INDEPENDENT_GO_NATIVE_NO_OBJECTIVE_SOURCE_PASS

git init -q "$RUNNER_TEMP/mg15/yggdrasil"
git -C "$RUNNER_TEMP/mg15/yggdrasil" remote add origin https://github.com/spoonman136668-ai/Yggdrasil.git
git -C "$RUNNER_TEMP/mg15/yggdrasil" fetch --no-tags --depth 1 origin 5a3f9f19142b97a11aa88da09eafbffdf932a024
git -C "$RUNNER_TEMP/mg15/yggdrasil" checkout --detach -q 5a3f9f19142b97a11aa88da09eafbffdf932a024
test "$(git -C "$RUNNER_TEMP/mg15/yggdrasil" hash-object research/native/itd02/r18/mission_cells.py)" = 531b4f258408eb38f38794f03a192aacdad42315
test "$(git -C "$RUNNER_TEMP/mg15/yggdrasil" hash-object research/native/itd02/r14/temporal_cells.py)" = 8cacaad50e8d484f72da5067ff1f03c187877f27
test "$(git -C "$RUNNER_TEMP/mg15/yggdrasil" hash-object research/native/itd02/r11/affordance_cells.py)" = 614c7dfb1b43f485009b70cb85e9b7b5119cafc2
echo MG15_INDEPENDENT_YGG_NATIVE_LOCAL_CELL_SOURCE_PASS

git init -q "$RUNNER_TEMP/mg15/collector"
git -C "$RUNNER_TEMP/mg15/collector" remote add origin https://github.com/spoonman136668-ai/Yggdrasil.git
git -C "$RUNNER_TEMP/mg15/collector" fetch --no-tags --depth 1 origin 9d18cd04e7264898a92e4e382da6fac4398ad584
git -C "$RUNNER_TEMP/mg15/collector" checkout --detach -q 9d18cd04e7264898a92e4e382da6fac4398ad584
test "$(git -C "$RUNNER_TEMP/mg15/collector" hash-object research/mass_r7c29/collect.py)" = 3e5c5ce30d15f3741b45a4900a8341bc339a85c9
test "$(git -C "$RUNNER_TEMP/mg15/collector" hash-object research/mass_r7c30/control.py)" = c3183c8b8e43ef0e3531df964c80f0370fbc4914
export MG03_COLLECTOR_ROOT="$RUNNER_TEMP/mg15/collector"
export PYTHONPATH="$RUNNER_TEMP/mg15/yggdrasil:$GITHUB_WORKSPACE/research/lcrm01"
echo MG15_FIT_ONLY_C29_1664_AND_EXPLICIT_UNASSISTED_CONVENTIONAL_PASS

python -B research/lcrm01/mg15_original_mission.py \
  --native-go-dk11 "$RUNNER_TEMP/mg15/native-dk14-source" \
  --output "$RUNNER_TEMP/mg15/first.json" > "$RUNNER_TEMP/mg15/first.log" 2>&1 || {
  cat "$RUNNER_TEMP/mg15/first.log"; exit 1;
}
cat "$RUNNER_TEMP/mg15/first.log"
python -B research/lcrm01/mg15_original_mission.py \
  --native-go-dk11 "$RUNNER_TEMP/mg15/native-dk14-source" \
  --output "$RUNNER_TEMP/mg15/second.json" > "$RUNNER_TEMP/mg15/second.log" 2>&1 || {
  cat "$RUNNER_TEMP/mg15/second.log"; exit 1;
}
cat "$RUNNER_TEMP/mg15/second.log"
python -B research/lcrm01/mg15_compare.py \
  --first "$RUNNER_TEMP/mg15/first.json" \
  --second "$RUNNER_TEMP/mg15/second.json" \
  --output "$RUNNER_TEMP/mg15/comparison.json"
test -z "$(git status --porcelain --untracked-files=all)"
echo MG15_ORIGINAL_SOURCE_EQUAL_RAW_PUBLIC_QUALIFIED__NOT_SCIENCE
