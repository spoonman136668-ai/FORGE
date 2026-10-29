#!/usr/bin/env bash
# MG09B original Farama source development; same public policy input, no live C29.
set -euo pipefail
cd "$GITHUB_WORKSPACE"
export PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 PIP_DISABLE_PIP_VERSION_CHECK=1

git merge-base --is-ancestor 58a5b03050857fa45828773b0001a39a932da7db "$GITHUB_SHA"
git merge-base --is-ancestor 9fd28525c5949cb536a94cf81bb892427945ef7d "$GITHUB_SHA"
test "$(git hash-object research/lcrm01/mg09b_raw_public_original_prereg.json)" = d1d69718d2225e0b0a8d7817f3810f5eb07b1783
test "$(git hash-object research/lcrm01/mg09b_go_bridge.go)" = f6e79f31638d31e78342f4ee6f2f5273dd441f53
test "$(git hash-object research/lcrm01/mg09b_original_public_comparison.py)" = 6b7e9b66fbcf9b08e23907799beb3312c560ee79
test "$(git hash-object research/lcrm01/mg09b_compare.py)" = 0609fbfc9423e31f33757e2a03957efdaa19fd27
test -z "$(git status --porcelain --untracked-files=all)"
echo MG09B_BEFORE_SOURCE_FROZEN_PREREG_AND_CODE_PINS_PASS

mkdir -p "$RUNNER_TEMP/mg09b/minigrid" "$RUNNER_TEMP/mg09b/wingless" "$RUNNER_TEMP/mg09b/yggdrasil" "$RUNNER_TEMP/mg09b/collector"
python -m pip install 'pip==24.0' 'setuptools==69.5.1' 'wheel==0.43.0'
python -m pip install 'numpy==1.26.4' 'gymnasium==1.1.1' 'pygame-ce==2.5.3'

git init -q "$RUNNER_TEMP/mg09b/minigrid"
git -C "$RUNNER_TEMP/mg09b/minigrid" remote add origin https://github.com/Farama-Foundation/Minigrid.git
git -C "$RUNNER_TEMP/mg09b/minigrid" fetch --no-tags --depth 1 origin 7f5853792ea7f04f75614661006d87fcf949f26d
git -C "$RUNNER_TEMP/mg09b/minigrid" checkout --detach -q 7f5853792ea7f04f75614661006d87fcf949f26d
test "$(git -C "$RUNNER_TEMP/mg09b/minigrid" hash-object minigrid/envs/doorkey.py)" = df5b29ef063be34e6d83b8b478e092c6e3e01512
test "$(git -C "$RUNNER_TEMP/mg09b/minigrid" hash-object minigrid/minigrid_env.py)" = eb29e9a902de0715ab77ec981a2113576d7664fa
python -m pip install --no-deps -e "$RUNNER_TEMP/mg09b/minigrid"
echo MG09B_AUTHENTIC_ORIGINAL_FARAMA_SOURCE_PASS

git init -q "$RUNNER_TEMP/mg09b/wingless"
git -C "$RUNNER_TEMP/mg09b/wingless" remote add origin https://github.com/spoonman136668-ai/Wingless.git
git -C "$RUNNER_TEMP/mg09b/wingless" fetch --no-tags --depth 1 origin e75cc1ac6d302f4926df9fd28f3aab02eded1de3
git -C "$RUNNER_TEMP/mg09b/wingless" checkout --detach -q e75cc1ac6d302f4926df9fd28f3aab02eded1de3
test "$(git -C "$RUNNER_TEMP/mg09b/wingless" hash-object research/native/itd02/dk11/continuity.go)" = 228027db110c3924aebf63420ff2caed47fe8c73
test "$(git -C "$RUNNER_TEMP/mg09b/wingless" hash-object research/native/itd02/dk10/temporal_policy.go)" = 3575ca351467ffd6200d277acf72b0d78dd54a52
test "$(git -C "$RUNNER_TEMP/mg09b/wingless" hash-object research/native/itd02/r8/online_beliefs.go)" = 6857ecbef2d63f459a432a5d68c7edda2b5347c4
(cd "$RUNNER_TEMP/mg09b/wingless" &&
  go test -count=1 ./research/native/itd02/dk11/... ./research/native/itd02/dk10/... &&
  go build -trimpath -o "$RUNNER_TEMP/mg09b/native-dk11-source" "$GITHUB_WORKSPACE/research/lcrm01/mg09b_go_bridge.go")
echo MG09B_INDEPENDENT_GO_NATIVE_NO_OBJECTIVE_SOURCE_PASS

git init -q "$RUNNER_TEMP/mg09b/yggdrasil"
git -C "$RUNNER_TEMP/mg09b/yggdrasil" remote add origin https://github.com/spoonman136668-ai/Yggdrasil.git
git -C "$RUNNER_TEMP/mg09b/yggdrasil" fetch --no-tags --depth 1 origin 630dde83f45d845488d59a36136d6c026e10880b
git -C "$RUNNER_TEMP/mg09b/yggdrasil" checkout --detach -q 630dde83f45d845488d59a36136d6c026e10880b
test "$(git -C "$RUNNER_TEMP/mg09b/yggdrasil" hash-object research/native/itd02/r15/continuity_cells.py)" = 6b31f4b0c301564b2793bef8a296a4e722825f01
test "$(git -C "$RUNNER_TEMP/mg09b/yggdrasil" hash-object research/native/itd02/r14/temporal_cells.py)" = 8cacaad50e8d484f72da5067ff1f03c187877f27
test "$(git -C "$RUNNER_TEMP/mg09b/yggdrasil" hash-object research/native/itd02/r11/affordance_cells.py)" = 614c7dfb1b43f485009b70cb85e9b7b5119cafc2
echo MG09B_INDEPENDENT_YGG_NATIVE_LOCAL_CELL_SOURCE_PASS

git init -q "$RUNNER_TEMP/mg09b/collector"
git -C "$RUNNER_TEMP/mg09b/collector" remote add origin https://github.com/spoonman136668-ai/Yggdrasil.git
git -C "$RUNNER_TEMP/mg09b/collector" fetch --no-tags --depth 1 origin 9d18cd04e7264898a92e4e382da6fac4398ad584
git -C "$RUNNER_TEMP/mg09b/collector" checkout --detach -q 9d18cd04e7264898a92e4e382da6fac4398ad584
test "$(git -C "$RUNNER_TEMP/mg09b/collector" hash-object research/mass_r7c29/collect.py)" = 3e5c5ce30d15f3741b45a4900a8341bc339a85c9
test "$(git -C "$RUNNER_TEMP/mg09b/collector" hash-object research/mass_r7c30/control.py)" = c3183c8b8e43ef0e3531df964c80f0370fbc4914
export MG03_COLLECTOR_ROOT="$RUNNER_TEMP/mg09b/collector"
export PYTHONPATH="$RUNNER_TEMP/mg09b/yggdrasil:$GITHUB_WORKSPACE/research/lcrm01"
echo MG09B_FIT_ONLY_C29_1664_AND_EXPLICIT_UNASSISTED_CONVENTIONAL_PASS

python -B research/lcrm01/mg09b_original_public_comparison.py \
  --native-go-dk11 "$RUNNER_TEMP/mg09b/native-dk11-source" \
  --output "$RUNNER_TEMP/mg09b/first.json" > "$RUNNER_TEMP/mg09b/first.log" 2>&1 || {
  cat "$RUNNER_TEMP/mg09b/first.log"; exit 1;
}
cat "$RUNNER_TEMP/mg09b/first.log"
python -B research/lcrm01/mg09b_original_public_comparison.py \
  --native-go-dk11 "$RUNNER_TEMP/mg09b/native-dk11-source" \
  --output "$RUNNER_TEMP/mg09b/second.json" > "$RUNNER_TEMP/mg09b/second.log" 2>&1 || {
  cat "$RUNNER_TEMP/mg09b/second.log"; exit 1;
}
cat "$RUNNER_TEMP/mg09b/second.log"
python -B research/lcrm01/mg09b_compare.py \
  --first "$RUNNER_TEMP/mg09b/first.json" \
  --second "$RUNNER_TEMP/mg09b/second.json" \
  --output "$RUNNER_TEMP/mg09b/comparison.json"
test -z "$(git status --porcelain --untracked-files=all)"
echo MG09B_ORIGINAL_SOURCE_EQUAL_RAW_PUBLIC_QUALIFIED__NOT_SCIENCE
