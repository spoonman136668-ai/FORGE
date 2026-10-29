#!/usr/bin/env bash
# Frozen source-only MG06 native-only + 32/64 capped assistance vs conventional.
set -euo pipefail
cd "$GITHUB_WORKSPACE"
export PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 PIP_DISABLE_PIP_VERSION_CHECK=1
git merge-base --is-ancestor 44897745c6cd9ab69f5e070bab11de79793ecfcd "$GITHUB_SHA"
git merge-base --is-ancestor 0cee622ed7c6b3a998ffdbb01d641aa1f007fe6b "$GITHUB_SHA"
git merge-base --is-ancestor 305ee7f12e1d0c190792252474e5e6c7f932e12d "$GITHUB_SHA"
git merge-base --is-ancestor 23040b1ef8441a3092b5cbff35156517e46e754d "$GITHUB_SHA"
git merge-base --is-ancestor d889f38332573e970048cf5719d67b82b3f22c70 "$GITHUB_SHA"
test "$(git hash-object research/lcrm01/mg05_native_only_capped_original_doorkey.py)" = d87445dc037cf3691b189d5ae4a1e44e15bde30f
test "$(git hash-object research/lcrm01/mg03_equal_public_doorkey_live.py)" = "$(git show 44897745c6cd9ab69f5e070bab11de79793ecfcd:research/lcrm01/mg03_equal_public_doorkey_live.py | git hash-object --stdin)"
test -z "$(git status --porcelain --untracked-files=all)"
echo MG06_FROZEN_PROTOCOL_CHRONOLOGY_AND_UNMODIFIED_MG04_PASS

mkdir -p "$RUNNER_TEMP/mg06/minigrid" "$RUNNER_TEMP/mg06/wingless" "$RUNNER_TEMP/mg06/yggdrasil" "$RUNNER_TEMP/mg06/collector"
python -m pip install 'pip==24.0' 'setuptools==69.5.1' 'wheel==0.43.0'
python -m pip install 'numpy==1.26.4' 'gymnasium==1.1.1' 'pygame-ce==2.5.3'
git init -q "$RUNNER_TEMP/mg06/minigrid"
git -C "$RUNNER_TEMP/mg06/minigrid" remote add origin https://github.com/Farama-Foundation/Minigrid.git
git -C "$RUNNER_TEMP/mg06/minigrid" fetch --no-tags --depth 1 origin 7f5853792ea7f04f75614661006d87fcf949f26d
git -C "$RUNNER_TEMP/mg06/minigrid" checkout --detach -q 7f5853792ea7f04f75614661006d87fcf949f26d
test "$(git -C "$RUNNER_TEMP/mg06/minigrid" hash-object minigrid/envs/doorkey.py)" = df5b29ef063be34e6d83b8b478e092c6e3e01512
test "$(git -C "$RUNNER_TEMP/mg06/minigrid" hash-object minigrid/wrappers.py)" = 1eb2da8fb612653c97f443ff6c7492ed3f1aaa80
python -m pip install --no-deps -e "$RUNNER_TEMP/mg06/minigrid"
echo MG06_ORIGINAL_AUTHENTIC_FARAMA_DOORKEY_PIN_PASS

git init -q "$RUNNER_TEMP/mg06/wingless"
git -C "$RUNNER_TEMP/mg06/wingless" remote add origin https://github.com/spoonman136668-ai/Wingless.git
git -C "$RUNNER_TEMP/mg06/wingless" fetch --no-tags --depth 1 origin f002936d7757af386143b748bbe4427214e5fd5b
git -C "$RUNNER_TEMP/mg06/wingless" checkout --detach -q f002936d7757af386143b748bbe4427214e5fd5b
test "$(git -C "$RUNNER_TEMP/mg06/wingless" hash-object research/native/itd02/dk9/explore_policy.go)" = b2914104945ecc29ecc265dbc9ce03f78170dc7a
test "$(git -C "$RUNNER_TEMP/mg06/wingless" hash-object research/native/itd02/dk9bridge/main.go)" = 930aee2066bfe71ef92dea804604ac3dbcfd4a25
test "$(git -C "$RUNNER_TEMP/mg06/wingless" hash-object research/native/itd02/r8/online_beliefs.go)" = 6857ecbef2d63f459a432a5d68c7edda2b5347c4
(cd "$RUNNER_TEMP/mg06/wingless" && go test -count=1 ./research/native/itd02/dk9/... && go build -trimpath -o "$RUNNER_TEMP/mg06/wingless-dk9-go" ./research/native/itd02/dk9bridge)
echo MG06_ORIGINAL_OPTIN_GO_DK8_ENGINEERING_PASS

git init -q "$RUNNER_TEMP/mg06/yggdrasil"
git -C "$RUNNER_TEMP/mg06/yggdrasil" remote add origin https://github.com/spoonman136668-ai/Yggdrasil.git
git -C "$RUNNER_TEMP/mg06/yggdrasil" fetch --no-tags --depth 1 origin b27372e6c670166749dc3dc41ab6cfe9b263292f
git -C "$RUNNER_TEMP/mg06/yggdrasil" checkout --detach -q b27372e6c670166749dc3dc41ab6cfe9b263292f
test "$(git -C "$RUNNER_TEMP/mg06/yggdrasil" hash-object research/native/itd02/r10/public_adapter.py)" = 3917d36ce9f86a2c1b998a0a2f93fb27674a9205
test "$(git -C "$RUNNER_TEMP/mg06/yggdrasil" hash-object research/native/itd02/r11/affordance_cells.py)" = 614c7dfb1b43f485009b70cb85e9b7b5119cafc2
test "$(git -C "$RUNNER_TEMP/mg06/yggdrasil" hash-object research/native/itd02/r12/outcome_choice.py)" = 2d19b28d6d4db1988ae908fe91be1a27ce4c1907
test "$(git -C "$RUNNER_TEMP/mg06/yggdrasil" hash-object research/native/itd02/r13/explore_choice.py)" = 51c421fbd34b5e88e02bf89acab0de7b11eee1c9

git init -q "$RUNNER_TEMP/mg06/collector"
git -C "$RUNNER_TEMP/mg06/collector" remote add origin https://github.com/spoonman136668-ai/Yggdrasil.git
git -C "$RUNNER_TEMP/mg06/collector" fetch --no-tags --depth 1 origin 9d18cd04e7264898a92e4e382da6fac4398ad584
git -C "$RUNNER_TEMP/mg06/collector" checkout --detach -q 9d18cd04e7264898a92e4e382da6fac4398ad584
test "$(git -C "$RUNNER_TEMP/mg06/collector" hash-object research/mass_r7c29/collect.py)" = 3e5c5ce30d15f3741b45a4900a8341bc339a85c9
test "$(git -C "$RUNNER_TEMP/mg06/collector" hash-object research/mass_r7c30/control.py)" = c3183c8b8e43ef0e3531df964c80f0370fbc4914
export MG03_COLLECTOR_ROOT="$RUNNER_TEMP/mg06/collector"
export PYTHONPATH="$RUNNER_TEMP/mg06/yggdrasil:$GITHUB_WORKSPACE/research/lcrm01"
echo MG06_INDEPENDENT_CONVENTIONAL_AND_ORIGINAL_YGGDRASIL_SOURCE_PINS_PASS

python -B research/lcrm01/mg06_original_doorkey_exploration.py \
 --wingless-dk9-go "$RUNNER_TEMP/mg06/wingless-dk9-go" \
 --output "$RUNNER_TEMP/mg06/first.json" > "$RUNNER_TEMP/mg06/first.log" 2>&1 || {
 cat "$RUNNER_TEMP/mg06/first.log"; exit 1;
}
cat "$RUNNER_TEMP/mg06/first.log"
python -B research/lcrm01/mg06_original_doorkey_exploration.py \
 --wingless-dk9-go "$RUNNER_TEMP/mg06/wingless-dk9-go" \
 --output "$RUNNER_TEMP/mg06/second.json" > "$RUNNER_TEMP/mg06/second.log" 2>&1 || {
 cat "$RUNNER_TEMP/mg06/second.log"; exit 1;
}
cat "$RUNNER_TEMP/mg06/second.log"
python -B research/lcrm01/mg06_compare.py \
 --first "$RUNNER_TEMP/mg06/first.json" \
 --second "$RUNNER_TEMP/mg06/second.json" \
 --output "$RUNNER_TEMP/mg06/comparison.json"
test -z "$(git status --porcelain --untracked-files=all)"
test -z "$(git -C "$RUNNER_TEMP/mg06/minigrid" status --porcelain --untracked-files=no)"
test -z "$(git -C "$RUNNER_TEMP/mg06/wingless" status --porcelain --untracked-files=no)"
test -z "$(git -C "$RUNNER_TEMP/mg06/yggdrasil" status --porcelain --untracked-files=no)"
test -z "$(git -C "$RUNNER_TEMP/mg06/collector" status --porcelain --untracked-files=no)"
echo MG06_AUTHENTIC_NATIVE_ONLY_SELF_SELECTED_ACTIONS_WITHOUT_EXTERNAL_COLLECTOR_NOT_SCIENCE
