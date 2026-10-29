#!/usr/bin/env bash
# MG11 original Farama source development; same public policy input, no live C29.
set -euo pipefail
cd "$GITHUB_WORKSPACE"
export PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 PIP_DISABLE_PIP_VERSION_CHECK=1

git merge-base --is-ancestor 58a5b03050857fa45828773b0001a39a932da7db "$GITHUB_SHA"
git merge-base --is-ancestor d3a686f0a40204943e6ea7dbf097b035c2ddb1f4 "$GITHUB_SHA"
test "$(git hash-object research/lcrm01/mg11_original_world_run_prereg.json)" = 7d186c0fec81de9d62ef4a70e6430b202a6b688c
test "$(git hash-object research/lcrm01/mg11_go_bridge.go)" = 6a439bb317189ca15c8fb741c5fa9f8937757793
test "$(git hash-object research/lcrm01/mg11_original_motion.py)" = 96000d69d1f98593bea13feb7dd1e88e6e48ce89
test "$(git hash-object research/lcrm01/mg11_compare.py)" = 6a3e418ccc2ec83259e6f4a82e7d9800fcfafb97
test -z "$(git status --porcelain --untracked-files=all)"
echo MG11_BEFORE_SOURCE_FROZEN_PREREG_AND_CODE_PINS_PASS

mkdir -p "$RUNNER_TEMP/mg11/minigrid" "$RUNNER_TEMP/mg11/wingless" "$RUNNER_TEMP/mg11/yggdrasil" "$RUNNER_TEMP/mg11/collector"
python -m pip install 'pip==24.0' 'setuptools==69.5.1' 'wheel==0.43.0'
python -m pip install 'numpy==1.26.4' 'gymnasium==1.1.1' 'pygame-ce==2.5.3'

git init -q "$RUNNER_TEMP/mg11/minigrid"
git -C "$RUNNER_TEMP/mg11/minigrid" remote add origin https://github.com/Farama-Foundation/Minigrid.git
git -C "$RUNNER_TEMP/mg11/minigrid" fetch --no-tags --depth 1 origin 7f5853792ea7f04f75614661006d87fcf949f26d
git -C "$RUNNER_TEMP/mg11/minigrid" checkout --detach -q 7f5853792ea7f04f75614661006d87fcf949f26d
test "$(git -C "$RUNNER_TEMP/mg11/minigrid" hash-object minigrid/envs/doorkey.py)" = df5b29ef063be34e6d83b8b478e092c6e3e01512
test "$(git -C "$RUNNER_TEMP/mg11/minigrid" hash-object minigrid/minigrid_env.py)" = eb29e9a902de0715ab77ec981a2113576d7664fa
python -m pip install --no-deps -e "$RUNNER_TEMP/mg11/minigrid"
echo MG11_AUTHENTIC_ORIGINAL_FARAMA_SOURCE_PASS

git init -q "$RUNNER_TEMP/mg11/wingless"
git -C "$RUNNER_TEMP/mg11/wingless" remote add origin https://github.com/spoonman136668-ai/Wingless.git
git -C "$RUNNER_TEMP/mg11/wingless" fetch --no-tags --depth 1 origin bdc02269856275399793d58892fbcfe4f5101623
git -C "$RUNNER_TEMP/mg11/wingless" checkout --detach -q bdc02269856275399793d58892fbcfe4f5101623
test "$(git -C "$RUNNER_TEMP/mg11/wingless" hash-object research/native/itd02/dk12/motion.go)" = f3d233136c4725304e36287465c0e05f1cf87336
test "$(git -C "$RUNNER_TEMP/mg11/wingless" hash-object research/native/itd02/dk10/temporal_policy.go)" = 3575ca351467ffd6200d277acf72b0d78dd54a52
test "$(git -C "$RUNNER_TEMP/mg11/wingless" hash-object research/native/itd02/r8/online_beliefs.go)" = 6857ecbef2d63f459a432a5d68c7edda2b5347c4
(cd "$RUNNER_TEMP/mg11/wingless" &&
  go test -count=1 ./research/native/itd02/dk12/... ./research/native/itd02/dk10/... &&
  go build -trimpath -o "$RUNNER_TEMP/mg11/native-dk11-source" "$GITHUB_WORKSPACE/research/lcrm01/mg11_go_bridge.go")
echo MG11_INDEPENDENT_GO_NATIVE_NO_OBJECTIVE_SOURCE_PASS

git init -q "$RUNNER_TEMP/mg11/yggdrasil"
git -C "$RUNNER_TEMP/mg11/yggdrasil" remote add origin https://github.com/spoonman136668-ai/Yggdrasil.git
git -C "$RUNNER_TEMP/mg11/yggdrasil" fetch --no-tags --depth 1 origin 02552f4b3a0ce2aebdcc20cfbde5f78af62e01ed
git -C "$RUNNER_TEMP/mg11/yggdrasil" checkout --detach -q 02552f4b3a0ce2aebdcc20cfbde5f78af62e01ed
test "$(git -C "$RUNNER_TEMP/mg11/yggdrasil" hash-object research/native/itd02/r16/motion_cells.py)" = 708d5d48c8aee5d1650d7fbb3983976197bc9f9a
test "$(git -C "$RUNNER_TEMP/mg11/yggdrasil" hash-object research/native/itd02/r14/temporal_cells.py)" = 8cacaad50e8d484f72da5067ff1f03c187877f27
test "$(git -C "$RUNNER_TEMP/mg11/yggdrasil" hash-object research/native/itd02/r11/affordance_cells.py)" = 614c7dfb1b43f485009b70cb85e9b7b5119cafc2
echo MG11_INDEPENDENT_YGG_NATIVE_LOCAL_CELL_SOURCE_PASS

git init -q "$RUNNER_TEMP/mg11/collector"
git -C "$RUNNER_TEMP/mg11/collector" remote add origin https://github.com/spoonman136668-ai/Yggdrasil.git
git -C "$RUNNER_TEMP/mg11/collector" fetch --no-tags --depth 1 origin 9d18cd04e7264898a92e4e382da6fac4398ad584
git -C "$RUNNER_TEMP/mg11/collector" checkout --detach -q 9d18cd04e7264898a92e4e382da6fac4398ad584
test "$(git -C "$RUNNER_TEMP/mg11/collector" hash-object research/mass_r7c29/collect.py)" = 3e5c5ce30d15f3741b45a4900a8341bc339a85c9
test "$(git -C "$RUNNER_TEMP/mg11/collector" hash-object research/mass_r7c30/control.py)" = c3183c8b8e43ef0e3531df964c80f0370fbc4914
export MG03_COLLECTOR_ROOT="$RUNNER_TEMP/mg11/collector"
export PYTHONPATH="$RUNNER_TEMP/mg11/yggdrasil:$GITHUB_WORKSPACE/research/lcrm01"
echo MG11_FIT_ONLY_C29_1664_AND_EXPLICIT_UNASSISTED_CONVENTIONAL_PASS

python -B research/lcrm01/mg11_original_motion.py \
  --native-go-dk11 "$RUNNER_TEMP/mg11/native-dk11-source" \
  --output "$RUNNER_TEMP/mg11/first.json" > "$RUNNER_TEMP/mg11/first.log" 2>&1 || {
  cat "$RUNNER_TEMP/mg11/first.log"; exit 1;
}
cat "$RUNNER_TEMP/mg11/first.log"
python -B research/lcrm01/mg11_original_motion.py \
  --native-go-dk11 "$RUNNER_TEMP/mg11/native-dk11-source" \
  --output "$RUNNER_TEMP/mg11/second.json" > "$RUNNER_TEMP/mg11/second.log" 2>&1 || {
  cat "$RUNNER_TEMP/mg11/second.log"; exit 1;
}
cat "$RUNNER_TEMP/mg11/second.log"
python -B research/lcrm01/mg11_compare.py \
  --first "$RUNNER_TEMP/mg11/first.json" \
  --second "$RUNNER_TEMP/mg11/second.json" \
  --output "$RUNNER_TEMP/mg11/comparison.json"
test -z "$(git status --porcelain --untracked-files=all)"
echo MG11_ORIGINAL_SOURCE_EQUAL_RAW_PUBLIC_QUALIFIED__NOT_SCIENCE
