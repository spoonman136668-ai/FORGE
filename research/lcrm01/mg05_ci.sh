#!/usr/bin/env bash
# Frozen source-only MG05 native-only + 32/64 capped assistance vs conventional.
set -euo pipefail
cd "$GITHUB_WORKSPACE"
export PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 PIP_DISABLE_PIP_VERSION_CHECK=1
git merge-base --is-ancestor f4e08d27776248f6f075db6fb93d3f4195bd941c "$GITHUB_SHA"
git merge-base --is-ancestor 8bda7a3a6899667f52b119b2d0b450c0b09522fe "$GITHUB_SHA"
git merge-base --is-ancestor c1b7fd442e8c41a51d42182afd48b84a3f3098e7 "$GITHUB_SHA"
git merge-base --is-ancestor 534f2640ae540486eafa6f2cb8afdc55eadd4c74 "$GITHUB_SHA"
git merge-base --is-ancestor 1e9b8609ce423d65bbda24ce3b70ddce77f3e27d "$GITHUB_SHA"
test "$(git hash-object research/lcrm01/mg04_public_effect_native_agency.py)" = 2866af2978fa37702bc58ffa59eab5db37a262d9
test "$(git hash-object research/lcrm01/mg03_equal_public_doorkey_live.py)" = "$(git show f4e08d27776248f6f075db6fb93d3f4195bd941c:research/lcrm01/mg03_equal_public_doorkey_live.py | git hash-object --stdin)"
test -z "$(git status --porcelain --untracked-files=all)"
echo MG05_FROZEN_PROTOCOL_CHRONOLOGY_AND_UNMODIFIED_MG04_PASS

mkdir -p "$RUNNER_TEMP/mg05/minigrid" "$RUNNER_TEMP/mg05/wingless" "$RUNNER_TEMP/mg05/yggdrasil" "$RUNNER_TEMP/mg05/collector"
python -m pip install 'pip==24.0' 'setuptools==69.5.1' 'wheel==0.43.0'
python -m pip install 'numpy==1.26.4' 'gymnasium==1.1.1' 'pygame-ce==2.5.3'
git init -q "$RUNNER_TEMP/mg05/minigrid"
git -C "$RUNNER_TEMP/mg05/minigrid" remote add origin https://github.com/Farama-Foundation/Minigrid.git
git -C "$RUNNER_TEMP/mg05/minigrid" fetch --no-tags --depth 1 origin 7f5853792ea7f04f75614661006d87fcf949f26d
git -C "$RUNNER_TEMP/mg05/minigrid" checkout --detach -q 7f5853792ea7f04f75614661006d87fcf949f26d
test "$(git -C "$RUNNER_TEMP/mg05/minigrid" hash-object minigrid/envs/doorkey.py)" = df5b29ef063be34e6d83b8b478e092c6e3e01512
test "$(git -C "$RUNNER_TEMP/mg05/minigrid" hash-object minigrid/wrappers.py)" = 1eb2da8fb612653c97f443ff6c7492ed3f1aaa80
python -m pip install --no-deps -e "$RUNNER_TEMP/mg05/minigrid"
echo MG05_ORIGINAL_AUTHENTIC_FARAMA_DOORKEY_PIN_PASS

git init -q "$RUNNER_TEMP/mg05/wingless"
git -C "$RUNNER_TEMP/mg05/wingless" remote add origin https://github.com/spoonman136668-ai/Wingless.git
git -C "$RUNNER_TEMP/mg05/wingless" fetch --no-tags --depth 1 origin 40fbec49fda33a04fea640535a8aaeaa29493cc7
git -C "$RUNNER_TEMP/mg05/wingless" checkout --detach -q 40fbec49fda33a04fea640535a8aaeaa29493cc7
test "$(git -C "$RUNNER_TEMP/mg05/wingless" hash-object research/native/itd02/dk8/effect_policy.go)" = 01484d331e9df9035be045b31d0e015f1f8652e2
test "$(git -C "$RUNNER_TEMP/mg05/wingless" hash-object research/native/itd02/dk8bridge/main.go)" = 6b7f5d7a586197c98a33ae193674dc1388b84ade
test "$(git -C "$RUNNER_TEMP/mg05/wingless" hash-object research/native/itd02/r8/online_beliefs.go)" = 6857ecbef2d63f459a432a5d68c7edda2b5347c4
(cd "$RUNNER_TEMP/mg05/wingless" && go test -count=1 ./research/native/itd02/dk8/... && go build -trimpath -o "$RUNNER_TEMP/mg05/wingless-dk8-go" ./research/native/itd02/dk8bridge)
echo MG05_ORIGINAL_OPTIN_GO_DK8_ENGINEERING_PASS

git init -q "$RUNNER_TEMP/mg05/yggdrasil"
git -C "$RUNNER_TEMP/mg05/yggdrasil" remote add origin https://github.com/spoonman136668-ai/Yggdrasil.git
git -C "$RUNNER_TEMP/mg05/yggdrasil" fetch --no-tags --depth 1 origin 6e2d4a219b1fb62e0124ba053b65b7e3fdd46546
git -C "$RUNNER_TEMP/mg05/yggdrasil" checkout --detach -q 6e2d4a219b1fb62e0124ba053b65b7e3fdd46546
test "$(git -C "$RUNNER_TEMP/mg05/yggdrasil" hash-object research/native/itd02/r10/public_adapter.py)" = 3917d36ce9f86a2c1b998a0a2f93fb27674a9205
test "$(git -C "$RUNNER_TEMP/mg05/yggdrasil" hash-object research/native/itd02/r11/affordance_cells.py)" = 614c7dfb1b43f485009b70cb85e9b7b5119cafc2
test "$(git -C "$RUNNER_TEMP/mg05/yggdrasil" hash-object research/native/itd02/r12/outcome_choice.py)" = 2d19b28d6d4db1988ae908fe91be1a27ce4c1907

git init -q "$RUNNER_TEMP/mg05/collector"
git -C "$RUNNER_TEMP/mg05/collector" remote add origin https://github.com/spoonman136668-ai/Yggdrasil.git
git -C "$RUNNER_TEMP/mg05/collector" fetch --no-tags --depth 1 origin 9d18cd04e7264898a92e4e382da6fac4398ad584
git -C "$RUNNER_TEMP/mg05/collector" checkout --detach -q 9d18cd04e7264898a92e4e382da6fac4398ad584
test "$(git -C "$RUNNER_TEMP/mg05/collector" hash-object research/mass_r7c29/collect.py)" = 3e5c5ce30d15f3741b45a4900a8341bc339a85c9
test "$(git -C "$RUNNER_TEMP/mg05/collector" hash-object research/mass_r7c30/control.py)" = c3183c8b8e43ef0e3531df964c80f0370fbc4914
export MG03_COLLECTOR_ROOT="$RUNNER_TEMP/mg05/collector"
export PYTHONPATH="$RUNNER_TEMP/mg05/yggdrasil:$GITHUB_WORKSPACE/research/lcrm01"
echo MG05_INDEPENDENT_CONVENTIONAL_AND_ORIGINAL_YGGDRASIL_SOURCE_PINS_PASS

python -B research/lcrm01/mg05_native_only_capped_original_doorkey.py \
 --wingless-dk8-go "$RUNNER_TEMP/mg05/wingless-dk8-go" \
 --output "$RUNNER_TEMP/mg05/first.json" > "$RUNNER_TEMP/mg05/first.log" 2>&1 || {
 cat "$RUNNER_TEMP/mg05/first.log"; exit 1;
}
cat "$RUNNER_TEMP/mg05/first.log"
python -B research/lcrm01/mg05_native_only_capped_original_doorkey.py \
 --wingless-dk8-go "$RUNNER_TEMP/mg05/wingless-dk8-go" \
 --output "$RUNNER_TEMP/mg05/second.json" > "$RUNNER_TEMP/mg05/second.log" 2>&1 || {
 cat "$RUNNER_TEMP/mg05/second.log"; exit 1;
}
cat "$RUNNER_TEMP/mg05/second.log"
python -B research/lcrm01/mg05_compare.py \
 --first "$RUNNER_TEMP/mg05/first.json" \
 --second "$RUNNER_TEMP/mg05/second.json" \
 --output "$RUNNER_TEMP/mg05/comparison.json"
test -z "$(git status --porcelain --untracked-files=all)"
test -z "$(git -C "$RUNNER_TEMP/mg05/minigrid" status --porcelain --untracked-files=no)"
test -z "$(git -C "$RUNNER_TEMP/mg05/wingless" status --porcelain --untracked-files=no)"
test -z "$(git -C "$RUNNER_TEMP/mg05/yggdrasil" status --porcelain --untracked-files=no)"
test -z "$(git -C "$RUNNER_TEMP/mg05/collector" status --porcelain --untracked-files=no)"
echo MG05_AUTHENTIC_NATIVE_ONLY_NO_HIDDEN_EXTERNAL_ACTIONS_AND_CAPPED_SOURCE_RUN_COMPLETE_NOT_SCIENCE
