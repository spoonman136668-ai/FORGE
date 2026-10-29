#!/usr/bin/env bash
# AC28 original Farama Unlock public-development transfer; train exclusively on unchanged DoorKey FIT.
set -euo pipefail
cd "$GITHUB_WORKSPACE"
export PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 PIP_DISABLE_PIP_VERSION_CHECK=1

git merge-base --is-ancestor 7293165c299f4ff9d5b945e0bb601d5b929219e1 HEAD
git merge-base --is-ancestor 1fc7706d55610aff29efa78c73418d4e79cff64c HEAD
git merge-base --is-ancestor 2761fabe41ff0c682e4b2bfa4b6725f7213bee87 HEAD
test "$(git hash-object research/lcrm01/mg12_go_bridge.go)" = d9d0846ddb480259213d085f94eeb2bfe85f6102
test "$(git hash-object research/lcrm01/mg12_original_successor.py)" = 974d14ffb01e7ea4af5d32d3ec7946ebe411f866
test "$(git hash-object research/lcrm01/ac28_unlock_transfer_prereg.json)" = 4392e2cd5ce80f2fc4f68808a5a7e5eb08ccab99
test "$(git hash-object research/lcrm01/ac28_unlock_original_transfer.py)" = 6a3339aef79c688de841c6372fc27f2a8a753f97
test "$(git hash-object research/lcrm01/ac28_unlock_compare.py)" = f44ae6549130637416e2403718906b9d7d2d7920
test "$(git hash-object research/lcrm01/test_ac28_unlock_sourceonly.py)" = 683116c5d335d62bd8903857e37292df471d10c0
python -B -m unittest discover -s research/lcrm01 -p "test_ac28_*.py" -v
echo AC28_BEFORE_SOURCE_FROZEN_PREREG_AND_CODE_PINS_PASS

mkdir -p "$RUNNER_TEMP/ac28/minigrid" "$RUNNER_TEMP/ac28/wingless" "$RUNNER_TEMP/ac28/yggdrasil" "$RUNNER_TEMP/ac28/collector"
python -m pip install 'pip==24.0' 'setuptools==69.5.1' 'wheel==0.43.0'
python -m pip install 'numpy==1.26.4' 'gymnasium==1.1.1' 'pygame-ce==2.5.3'

git init -q "$RUNNER_TEMP/ac28/minigrid"
git -C "$RUNNER_TEMP/ac28/minigrid" remote add origin https://github.com/Farama-Foundation/Minigrid.git
git -C "$RUNNER_TEMP/ac28/minigrid" fetch --no-tags --depth 1 origin 7f5853792ea7f04f75614661006d87fcf949f26d
git -C "$RUNNER_TEMP/ac28/minigrid" checkout --detach -q 7f5853792ea7f04f75614661006d87fcf949f26d
test "$(git -C "$RUNNER_TEMP/ac28/minigrid" hash-object minigrid/envs/doorkey.py)" = df5b29ef063be34e6d83b8b478e092c6e3e01512
test "$(git -C "$RUNNER_TEMP/ac28/minigrid" hash-object minigrid/envs/unlock.py)" = 974acd6f59d03a3accde838918cf154fedc94c24
test "$(git -C "$RUNNER_TEMP/ac28/minigrid" hash-object minigrid/minigrid_env.py)" = eb29e9a902de0715ab77ec981a2113576d7664fa
python -m pip install --no-deps -e "$RUNNER_TEMP/ac28/minigrid"
echo AC28_AUTHENTIC_ORIGINAL_FARAMA_SOURCE_PASS

git init -q "$RUNNER_TEMP/ac28/wingless"
git -C "$RUNNER_TEMP/ac28/wingless" remote add origin https://github.com/spoonman136668-ai/Wingless.git
git -C "$RUNNER_TEMP/ac28/wingless" fetch --no-tags --depth 1 origin 2992a25e3fe05783bfa80ecf70d737bb2a21e281
git -C "$RUNNER_TEMP/ac28/wingless" checkout --detach -q 2992a25e3fe05783bfa80ecf70d737bb2a21e281
test "$(git -C "$RUNNER_TEMP/ac28/wingless" hash-object research/native/itd02/dk13/successor.go)" = b4c0e029f45448117dbf9870b85f6551acf12822
test "$(git -C "$RUNNER_TEMP/ac28/wingless" hash-object research/native/itd02/dk10/temporal_policy.go)" = 3575ca351467ffd6200d277acf72b0d78dd54a52
test "$(git -C "$RUNNER_TEMP/ac28/wingless" hash-object research/native/itd02/r8/online_beliefs.go)" = 6857ecbef2d63f459a432a5d68c7edda2b5347c4
(cd "$RUNNER_TEMP/ac28/wingless" &&
  go test -count=1 ./research/native/itd02/dk13/... ./research/native/itd02/dk10/... &&
  go build -trimpath -o "$RUNNER_TEMP/ac28/native-dk13-source" "$GITHUB_WORKSPACE/research/lcrm01/mg12_go_bridge.go")
echo AC28_INDEPENDENT_GO_NATIVE_NO_OBJECTIVE_SOURCE_PASS

git init -q "$RUNNER_TEMP/ac28/yggdrasil"
git -C "$RUNNER_TEMP/ac28/yggdrasil" remote add origin https://github.com/spoonman136668-ai/Yggdrasil.git
git -C "$RUNNER_TEMP/ac28/yggdrasil" fetch --no-tags --depth 1 origin 770244b04d011466458b2335d3951daf7653dc8f
git -C "$RUNNER_TEMP/ac28/yggdrasil" checkout --detach -q 770244b04d011466458b2335d3951daf7653dc8f
test "$(git -C "$RUNNER_TEMP/ac28/yggdrasil" hash-object research/native/itd02/r17/successor_cells.py)" = 9354a1f0b732100ab943a5caee80b3849e3c1ea0
test "$(git -C "$RUNNER_TEMP/ac28/yggdrasil" hash-object research/native/itd02/r14/temporal_cells.py)" = 8cacaad50e8d484f72da5067ff1f03c187877f27
test "$(git -C "$RUNNER_TEMP/ac28/yggdrasil" hash-object research/native/itd02/r11/affordance_cells.py)" = 614c7dfb1b43f485009b70cb85e9b7b5119cafc2
echo AC28_INDEPENDENT_YGG_NATIVE_LOCAL_CELL_SOURCE_PASS

git init -q "$RUNNER_TEMP/ac28/collector"
git -C "$RUNNER_TEMP/ac28/collector" remote add origin https://github.com/spoonman136668-ai/Yggdrasil.git
git -C "$RUNNER_TEMP/ac28/collector" fetch --no-tags --depth 1 origin 9d18cd04e7264898a92e4e382da6fac4398ad584
git -C "$RUNNER_TEMP/ac28/collector" checkout --detach -q 9d18cd04e7264898a92e4e382da6fac4398ad584
test "$(git -C "$RUNNER_TEMP/ac28/collector" hash-object research/mass_r7c29/collect.py)" = 3e5c5ce30d15f3741b45a4900a8341bc339a85c9
test "$(git -C "$RUNNER_TEMP/ac28/collector" hash-object research/mass_r7c30/control.py)" = c3183c8b8e43ef0e3531df964c80f0370fbc4914
export MG03_COLLECTOR_ROOT="$RUNNER_TEMP/ac28/collector"
export PYTHONPATH="$RUNNER_TEMP/ac28/yggdrasil:$GITHUB_WORKSPACE/research/lcrm01"
echo AC28_FIT_ONLY_C29_1664_AND_EXPLICIT_UNASSISTED_CONVENTIONAL_PASS

python -B research/lcrm01/ac28_unlock_original_transfer.py \
  --native-go-dk11 "$RUNNER_TEMP/ac28/native-dk13-source" \
  --output "$RUNNER_TEMP/ac28/first.json" > "$RUNNER_TEMP/ac28/first.log" 2>&1 || {
  cat "$RUNNER_TEMP/ac28/first.log"; exit 1;
}
cat "$RUNNER_TEMP/ac28/first.log"
python -B research/lcrm01/ac28_unlock_original_transfer.py \
  --native-go-dk11 "$RUNNER_TEMP/ac28/native-dk13-source" \
  --output "$RUNNER_TEMP/ac28/second.json" > "$RUNNER_TEMP/ac28/second.log" 2>&1 || {
  cat "$RUNNER_TEMP/ac28/second.log"; exit 1;
}
cat "$RUNNER_TEMP/ac28/second.log"
python -B research/lcrm01/ac28_unlock_compare.py \
  --first "$RUNNER_TEMP/ac28/first.json" \
  --second "$RUNNER_TEMP/ac28/second.json" \
  --output "$RUNNER_TEMP/ac28/comparison.json"
test -z "$(git status --porcelain --untracked-files=all)"
echo AC28_ORIGINAL_SOURCE_EQUAL_RAW_PUBLIC_QUALIFIED__NOT_SCIENCE
