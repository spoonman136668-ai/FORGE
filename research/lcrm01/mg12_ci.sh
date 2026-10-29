#!/usr/bin/env bash
# MG12 original Farama source development; same public policy input, no live C29.
set -euo pipefail
cd "$GITHUB_WORKSPACE"
export PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 PIP_DISABLE_PIP_VERSION_CHECK=1

git merge-base --is-ancestor 58a5b03050857fa45828773b0001a39a932da7db "$GITHUB_SHA"
git merge-base --is-ancestor cc2976ff7de612770e86737499393f3815d0433a "$GITHUB_SHA"
test "$(git hash-object research/lcrm01/mg12_original_successor_run_prereg.json)" = f0bb8b6f9e575830d09d60e890a19beb3cb72107
test "$(git hash-object research/lcrm01/mg12_go_bridge.go)" = d9d0846ddb480259213d085f94eeb2bfe85f6102
test "$(git hash-object research/lcrm01/mg12_original_successor.py)" = 974d14ffb01e7ea4af5d32d3ec7946ebe411f866
test "$(git hash-object research/lcrm01/mg12_compare.py)" = d7cc00fc070a13c01094c5464c9e6bf89c867d3f
test -z "$(git status --porcelain --untracked-files=all)"
echo MG12_BEFORE_SOURCE_FROZEN_PREREG_AND_CODE_PINS_PASS

mkdir -p "$RUNNER_TEMP/mg12/minigrid" "$RUNNER_TEMP/mg12/wingless" "$RUNNER_TEMP/mg12/yggdrasil" "$RUNNER_TEMP/mg12/collector"
python -m pip install 'pip==24.0' 'setuptools==69.5.1' 'wheel==0.43.0'
python -m pip install 'numpy==1.26.4' 'gymnasium==1.1.1' 'pygame-ce==2.5.3'

git init -q "$RUNNER_TEMP/mg12/minigrid"
git -C "$RUNNER_TEMP/mg12/minigrid" remote add origin https://github.com/Farama-Foundation/Minigrid.git
git -C "$RUNNER_TEMP/mg12/minigrid" fetch --no-tags --depth 1 origin 7f5853792ea7f04f75614661006d87fcf949f26d
git -C "$RUNNER_TEMP/mg12/minigrid" checkout --detach -q 7f5853792ea7f04f75614661006d87fcf949f26d
test "$(git -C "$RUNNER_TEMP/mg12/minigrid" hash-object minigrid/envs/doorkey.py)" = df5b29ef063be34e6d83b8b478e092c6e3e01512
test "$(git -C "$RUNNER_TEMP/mg12/minigrid" hash-object minigrid/minigrid_env.py)" = eb29e9a902de0715ab77ec981a2113576d7664fa
python -m pip install --no-deps -e "$RUNNER_TEMP/mg12/minigrid"
echo MG12_AUTHENTIC_ORIGINAL_FARAMA_SOURCE_PASS

git init -q "$RUNNER_TEMP/mg12/wingless"
git -C "$RUNNER_TEMP/mg12/wingless" remote add origin https://github.com/spoonman136668-ai/Wingless.git
git -C "$RUNNER_TEMP/mg12/wingless" fetch --no-tags --depth 1 origin 2992a25e3fe05783bfa80ecf70d737bb2a21e281
git -C "$RUNNER_TEMP/mg12/wingless" checkout --detach -q 2992a25e3fe05783bfa80ecf70d737bb2a21e281
test "$(git -C "$RUNNER_TEMP/mg12/wingless" hash-object research/native/itd02/dk13/successor.go)" = b4c0e029f45448117dbf9870b85f6551acf12822
test "$(git -C "$RUNNER_TEMP/mg12/wingless" hash-object research/native/itd02/dk10/temporal_policy.go)" = 3575ca351467ffd6200d277acf72b0d78dd54a52
test "$(git -C "$RUNNER_TEMP/mg12/wingless" hash-object research/native/itd02/r8/online_beliefs.go)" = 6857ecbef2d63f459a432a5d68c7edda2b5347c4
(cd "$RUNNER_TEMP/mg12/wingless" &&
  go test -count=1 ./research/native/itd02/dk13/... ./research/native/itd02/dk10/... &&
  go build -trimpath -o "$RUNNER_TEMP/mg12/native-dk13-source" "$GITHUB_WORKSPACE/research/lcrm01/mg12_go_bridge.go")
echo MG12_INDEPENDENT_GO_NATIVE_NO_OBJECTIVE_SOURCE_PASS

git init -q "$RUNNER_TEMP/mg12/yggdrasil"
git -C "$RUNNER_TEMP/mg12/yggdrasil" remote add origin https://github.com/spoonman136668-ai/Yggdrasil.git
git -C "$RUNNER_TEMP/mg12/yggdrasil" fetch --no-tags --depth 1 origin 770244b04d011466458b2335d3951daf7653dc8f
git -C "$RUNNER_TEMP/mg12/yggdrasil" checkout --detach -q 770244b04d011466458b2335d3951daf7653dc8f
test "$(git -C "$RUNNER_TEMP/mg12/yggdrasil" hash-object research/native/itd02/r17/successor_cells.py)" = 9354a1f0b732100ab943a5caee80b3849e3c1ea0
test "$(git -C "$RUNNER_TEMP/mg12/yggdrasil" hash-object research/native/itd02/r14/temporal_cells.py)" = 8cacaad50e8d484f72da5067ff1f03c187877f27
test "$(git -C "$RUNNER_TEMP/mg12/yggdrasil" hash-object research/native/itd02/r11/affordance_cells.py)" = 614c7dfb1b43f485009b70cb85e9b7b5119cafc2
echo MG12_INDEPENDENT_YGG_NATIVE_LOCAL_CELL_SOURCE_PASS

git init -q "$RUNNER_TEMP/mg12/collector"
git -C "$RUNNER_TEMP/mg12/collector" remote add origin https://github.com/spoonman136668-ai/Yggdrasil.git
git -C "$RUNNER_TEMP/mg12/collector" fetch --no-tags --depth 1 origin 9d18cd04e7264898a92e4e382da6fac4398ad584
git -C "$RUNNER_TEMP/mg12/collector" checkout --detach -q 9d18cd04e7264898a92e4e382da6fac4398ad584
test "$(git -C "$RUNNER_TEMP/mg12/collector" hash-object research/mass_r7c29/collect.py)" = 3e5c5ce30d15f3741b45a4900a8341bc339a85c9
test "$(git -C "$RUNNER_TEMP/mg12/collector" hash-object research/mass_r7c30/control.py)" = c3183c8b8e43ef0e3531df964c80f0370fbc4914
export MG03_COLLECTOR_ROOT="$RUNNER_TEMP/mg12/collector"
export PYTHONPATH="$RUNNER_TEMP/mg12/yggdrasil:$GITHUB_WORKSPACE/research/lcrm01"
echo MG12_FIT_ONLY_C29_1664_AND_EXPLICIT_UNASSISTED_CONVENTIONAL_PASS

python -B research/lcrm01/mg12_original_successor.py \
  --native-go-dk11 "$RUNNER_TEMP/mg12/native-dk13-source" \
  --output "$RUNNER_TEMP/mg12/first.json" > "$RUNNER_TEMP/mg12/first.log" 2>&1 || {
  cat "$RUNNER_TEMP/mg12/first.log"; exit 1;
}
cat "$RUNNER_TEMP/mg12/first.log"
python -B research/lcrm01/mg12_original_successor.py \
  --native-go-dk11 "$RUNNER_TEMP/mg12/native-dk13-source" \
  --output "$RUNNER_TEMP/mg12/second.json" > "$RUNNER_TEMP/mg12/second.log" 2>&1 || {
  cat "$RUNNER_TEMP/mg12/second.log"; exit 1;
}
cat "$RUNNER_TEMP/mg12/second.log"
python -B research/lcrm01/mg12_compare.py \
  --first "$RUNNER_TEMP/mg12/first.json" \
  --second "$RUNNER_TEMP/mg12/second.json" \
  --output "$RUNNER_TEMP/mg12/comparison.json"
test -z "$(git status --porcelain --untracked-files=all)"
echo MG12_ORIGINAL_SOURCE_EQUAL_RAW_PUBLIC_QUALIFIED__NOT_SCIENCE
