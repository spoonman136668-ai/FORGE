#!/usr/bin/env bash
# AC32 authentic original-world development; NEVER protected scientific first use.
set -euo pipefail
cd "$GITHUB_WORKSPACE"
export PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 PIP_DISABLE_PIP_VERSION_CHECK=1
git merge-base --is-ancestor 28fb7f8925535d0bfc21565e4eb00a6c965031f1 HEAD
git merge-base --is-ancestor 05b0de5c965fdc01d2b3936852bf9bc54d534da2 HEAD
test "$(git hash-object research/lcrm01/ac32_frozen_original_worlds.json)" = 1c6faa55677e1227a70b85345a0bd1ed7ecdba90
test "$(git hash-object research/lcrm01/ac31_native_go_bridge.go)" = 7b42d310ffe2cc6573d1ed085c0cbae2dce3ca6d
test "$(git hash-object research/lcrm01/ac32_original_multifamily.py)" = c91b372ac4acbaed879ef9d9606684b7ab81e411
test "$(git hash-object research/lcrm01/ac32_original_compare.py)" = 0d10b413cea1ecb203f72b4f3c63c56ef987b2f0
test "$(git hash-object research/lcrm01/test_ac32_frozen_preflight.py)" = fc3e492204f42a1d09f9d94fd9f475031a60b4ff
test -z "$(git status --porcelain --untracked-files=all)"
python -B -m unittest discover -s research/lcrm01 -p 'test_ac32_frozen_preflight.py' -v
echo AC32_FROZEN_BEFORE_FIRST_REAL_ORIGINAL_SOURCE_CALL=PASS

mkdir -p "$RUNNER_TEMP/ac32/minigrid" "$RUNNER_TEMP/ac32/wingless" "$RUNNER_TEMP/ac32/yggdrasil" "$RUNNER_TEMP/ac32/collector"
python -m pip install 'pip==24.0' 'setuptools==69.5.1' 'wheel==0.43.0'
python -m pip install 'numpy==1.26.4' 'gymnasium==1.1.1' 'pygame-ce==2.5.3'
git init -q "$RUNNER_TEMP/ac32/minigrid"
git -C "$RUNNER_TEMP/ac32/minigrid" remote add origin https://github.com/Farama-Foundation/Minigrid.git
git -C "$RUNNER_TEMP/ac32/minigrid" fetch --no-tags --depth 1 origin 7f5853792ea7f04f75614661006d87fcf949f26d
git -C "$RUNNER_TEMP/ac32/minigrid" checkout --detach -q 7f5853792ea7f04f75614661006d87fcf949f26d
test "$(git -C "$RUNNER_TEMP/ac32/minigrid" hash-object minigrid/envs/doorkey.py)" = df5b29ef063be34e6d83b8b478e092c6e3e01512
test "$(git -C "$RUNNER_TEMP/ac32/minigrid" hash-object minigrid/envs/empty.py)" = 8810bb0fa156d18475022edd8859b135ef745a5f
test "$(git -C "$RUNNER_TEMP/ac32/minigrid" hash-object minigrid/envs/unlock.py)" = 974acd6f59d03a3accde838918cf154fedc94c24
test "$(git -C "$RUNNER_TEMP/ac32/minigrid" hash-object minigrid/minigrid_env.py)" = eb29e9a902de0715ab77ec981a2113576d7664fa
python -m pip install --no-deps -e "$RUNNER_TEMP/ac32/minigrid"
echo AC32_PINNED_ORIGINAL_FARAMA_THREE_FAMILIES=PASS

git init -q "$RUNNER_TEMP/ac32/wingless"
git -C "$RUNNER_TEMP/ac32/wingless" remote add origin https://github.com/spoonman136668-ai/Wingless.git
git -C "$RUNNER_TEMP/ac32/wingless" fetch --no-tags --depth 1 origin 9a712f574e48a3d47f2d986d8be3d0eda2b3b9bd
git -C "$RUNNER_TEMP/ac32/wingless" checkout --detach -q 9a712f574e48a3d47f2d986d8be3d0eda2b3b9bd
test "$(git -C "$RUNNER_TEMP/ac32/wingless" hash-object research/native/itd02/dk15/mission_actor.go)" = 104e039c5c172a1bd60f03efb49ac0a877ff86fc
test "$(git -C "$RUNNER_TEMP/ac32/wingless" hash-object research/native/itd02/dk13/successor.go)" = b4c0e029f45448117dbf9870b85f6551acf12822
test "$(git -C "$RUNNER_TEMP/ac32/wingless" hash-object research/native/itd02/dk14/public_boundary.go)" = 5b7a9212ef67b515f6cae4d37424e2591a1a18a1
(cd "$RUNNER_TEMP/ac32/wingless" &&
 go test -count=1 ./research/native/itd02/dk15/... ./research/native/itd02/dk13/... &&
 go build -trimpath -o "$RUNNER_TEMP/ac32/native-dk15" "$GITHUB_WORKSPACE/research/lcrm01/ac31_native_go_bridge.go")
echo AC32_QUALIFIED_ORIGINAL_GO_DK15_SOURCE=PASS

git init -q "$RUNNER_TEMP/ac32/yggdrasil"
git -C "$RUNNER_TEMP/ac32/yggdrasil" remote add origin https://github.com/spoonman136668-ai/Yggdrasil.git
git -C "$RUNNER_TEMP/ac32/yggdrasil" fetch --no-tags --depth 1 origin 2225c19a8a6c55bfdf6785ffc1a26b450fc6f24e
git -C "$RUNNER_TEMP/ac32/yggdrasil" checkout --detach -q 2225c19a8a6c55bfdf6785ffc1a26b450fc6f24e
test "$(git -C "$RUNNER_TEMP/ac32/yggdrasil" hash-object research/native/itd02/r19/mission_actor.py)" = 0f8ac093fb0cab7388c8af869c5e40f6edc9f5cb
test "$(git -C "$RUNNER_TEMP/ac32/yggdrasil" hash-object research/native/itd02/r17/successor_cells.py)" = 9354a1f0b732100ab943a5caee80b3849e3c1ea0
test "$(git -C "$RUNNER_TEMP/ac32/yggdrasil" hash-object research/native/itd02/r18/public_boundary.py)" = 49477595ebe3f07eb9a2ec7a1d85c5bd1972de84
echo AC32_QUALIFIED_ORIGINAL_YGG_R19_SOURCE=PASS

git init -q "$RUNNER_TEMP/ac32/collector"
git -C "$RUNNER_TEMP/ac32/collector" remote add origin https://github.com/spoonman136668-ai/Yggdrasil.git
git -C "$RUNNER_TEMP/ac32/collector" fetch --no-tags --depth 1 origin 9d18cd04e7264898a92e4e382da6fac4398ad584
git -C "$RUNNER_TEMP/ac32/collector" checkout --detach -q 9d18cd04e7264898a92e4e382da6fac4398ad584
test "$(git -C "$RUNNER_TEMP/ac32/collector" hash-object research/mass_r7c29/collect.py)" = 3e5c5ce30d15f3741b45a4900a8341bc339a85c9
test "$(git -C "$RUNNER_TEMP/ac32/collector" hash-object research/mass_r7c30/control.py)" = c3183c8b8e43ef0e3531df964c80f0370fbc4914
export MG03_COLLECTOR_ROOT="$RUNNER_TEMP/ac32/collector"
export PYTHONPATH="$RUNNER_TEMP/ac32/yggdrasil:$GITHUB_WORKSPACE/research/lcrm01"
echo AC32_FIVE_ORIGINAL_PUBLIC_SOURCE_ACTORS_UNMODIFIED=PASS

python -B research/lcrm01/ac32_original_multifamily.py --native-go-dk11 "$RUNNER_TEMP/ac32/native-dk15" --output "$RUNNER_TEMP/ac32/first.json" > "$RUNNER_TEMP/ac32/first.log" 2>&1 || {
 cat "$RUNNER_TEMP/ac32/first.log"; exit 1;
}
cat "$RUNNER_TEMP/ac32/first.log"
python -B research/lcrm01/ac32_original_multifamily.py --native-go-dk11 "$RUNNER_TEMP/ac32/native-dk15" --output "$RUNNER_TEMP/ac32/second.json" > "$RUNNER_TEMP/ac32/second.log" 2>&1 || {
 cat "$RUNNER_TEMP/ac32/second.log"; exit 1;
}
cat "$RUNNER_TEMP/ac32/second.log"
python -B research/lcrm01/ac32_original_compare.py --first "$RUNNER_TEMP/ac32/first.json" --second "$RUNNER_TEMP/ac32/second.json" --output "$RUNNER_TEMP/ac32/comparison.json"
test -z "$(git status --porcelain --untracked-files=all)"
echo AC32_TWO_GENUINE_ORIGINAL_SOURCE_PROCESSES_QUALIFIED__NOT_SCIENCE
