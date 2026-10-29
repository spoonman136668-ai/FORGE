#!/usr/bin/env bash
# MG03 source-only original Farama DoorKey, equal public 7x7 direction mission.
# Original Wingless R8 remains 3-action: never misstate DK7 Go as restored R8.
set -euo pipefail
cd "$GITHUB_WORKSPACE"
export PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 PIP_DISABLE_PIP_VERSION_CHECK=1
git merge-base --is-ancestor 50e2a2d34e8e358624594eed3d57d098c89fa3b1 "$GITHUB_SHA"
git merge-base --is-ancestor 7145a1731949789b28ea5f2fdc8a614366e93b67 "$GITHUB_SHA"
git merge-base --is-ancestor 703a42d85850c2fa19a47904fd99f9c255fa375d "$GITHUB_SHA"
git merge-base --is-ancestor bcff656ce9eace507ead9f1730ec9c99bf7a7e5c "$GITHUB_SHA"
test "$(git hash-object research/lcrm01/mg01_paired_live_minigrid.py)" = 49ca1b4b9b635f402f73e5f123f9e34093025cab
test "$(git hash-object research/lcrm01/mg02_r8_paired_live.py)" = "$(git show 50e2a2d34e8e358624594eed3d57d098c89fa3b1:research/lcrm01/mg02_r8_paired_live.py | git hash-object --stdin)"
echo MG03_FROZEN_PREREG_AND_PARENT_SOURCE_PASS

mkdir -p "$RUNNER_TEMP/mg03/minigrid" "$RUNNER_TEMP/mg03/wingless" "$RUNNER_TEMP/mg03/ygg-r12" "$RUNNER_TEMP/mg03/collector"
python -m pip install 'pip==24.0' 'setuptools==69.5.1' 'wheel==0.43.0'
python -m pip install 'numpy==1.26.4' 'gymnasium==1.1.1' 'pygame-ce==2.5.3'
git init -q "$RUNNER_TEMP/mg03/minigrid"
git -C "$RUNNER_TEMP/mg03/minigrid" remote add origin https://github.com/Farama-Foundation/Minigrid.git
git -C "$RUNNER_TEMP/mg03/minigrid" fetch --no-tags --depth 1 origin 7f5853792ea7f04f75614661006d87fcf949f26d
git -C "$RUNNER_TEMP/mg03/minigrid" checkout --detach -q 7f5853792ea7f04f75614661006d87fcf949f26d
test "$(git -C "$RUNNER_TEMP/mg03/minigrid" hash-object minigrid/envs/doorkey.py)" = df5b29ef063be34e6d83b8b478e092c6e3e01512
test "$(git -C "$RUNNER_TEMP/mg03/minigrid" hash-object minigrid/wrappers.py)" = 1eb2da8fb612653c97f443ff6c7492ed3f1aaa80
test "$(git -C "$RUNNER_TEMP/mg03/minigrid" hash-object minigrid/minigrid_env.py)" = eb29e9a902de0715ab77ec981a2113576d7664fa
python -m pip install --no-deps -e "$RUNNER_TEMP/mg03/minigrid"
echo MG03_INDEPENDENT_AUTHENTIC_SOURCE_FARAMA_DOORKEY_PASS

git init -q "$RUNNER_TEMP/mg03/wingless"
git -C "$RUNNER_TEMP/mg03/wingless" remote add origin https://github.com/spoonman136668-ai/Wingless.git
git -C "$RUNNER_TEMP/mg03/wingless" fetch --no-tags --depth 1 origin 200c622367f9d748bf9107c941684a4cd92aef34
git -C "$RUNNER_TEMP/mg03/wingless" checkout --detach -q 200c622367f9d748bf9107c941684a4cd92aef34
test "$(git -C "$RUNNER_TEMP/mg03/wingless" hash-object research/native/itd02/dk7/public_policy.go)" = b61ae9118dc1dae521f84ec44c72c891ce84df8c
test "$(git -C "$RUNNER_TEMP/mg03/wingless" hash-object research/native/itd02/dk7bridge/main.go)" = 57bb90bdaeab3c31d0427b24945907ea18664db6
test "$(git -C "$RUNNER_TEMP/mg03/wingless" hash-object research/native/itd02/r8/online_beliefs.go)" = 6857ecbef2d63f459a432a5d68c7edda2b5347c4
(cd "$RUNNER_TEMP/mg03/wingless" && go test -count=1 ./research/native/itd02/dk7/... && go build -trimpath -o "$RUNNER_TEMP/mg03/wingless-dk7" ./research/native/itd02/dk7bridge)
export MG03_WINGLESS_DK7="$RUNNER_TEMP/mg03/wingless-dk7"
echo MG03_WINGLESS_GO_SOURCE_ONLY_SEVEN_ACTION_NATIVE_PASS

git init -q "$RUNNER_TEMP/mg03/ygg-r12"
git -C "$RUNNER_TEMP/mg03/ygg-r12" remote add origin https://github.com/spoonman136668-ai/Yggdrasil.git
git -C "$RUNNER_TEMP/mg03/ygg-r12" fetch --no-tags --depth 1 origin 6e2d4a219b1fb62e0124ba053b65b7e3fdd46546
git -C "$RUNNER_TEMP/mg03/ygg-r12" checkout --detach -q 6e2d4a219b1fb62e0124ba053b65b7e3fdd46546
test "$(git -C "$RUNNER_TEMP/mg03/ygg-r12" hash-object research/native/itd02/r10/public_adapter.py)" = 3917d36ce9f86a2c1b998a0a2f93fb27674a9205
test "$(git -C "$RUNNER_TEMP/mg03/ygg-r12" hash-object research/native/itd02/r11/affordance_cells.py)" = 614c7dfb1b43f485009b70cb85e9b7b5119cafc2
test "$(git -C "$RUNNER_TEMP/mg03/ygg-r12" hash-object research/native/itd02/r12/outcome_choice.py)" = 2d19b28d6d4db1988ae908fe91be1a27ce4c1907

git init -q "$RUNNER_TEMP/mg03/collector"
git -C "$RUNNER_TEMP/mg03/collector" remote add origin https://github.com/spoonman136668-ai/Yggdrasil.git
git -C "$RUNNER_TEMP/mg03/collector" fetch --no-tags --depth 1 origin 9d18cd04e7264898a92e4e382da6fac4398ad584
git -C "$RUNNER_TEMP/mg03/collector" checkout --detach -q 9d18cd04e7264898a92e4e382da6fac4398ad584
test "$(git -C "$RUNNER_TEMP/mg03/collector" hash-object research/mass_r7c29/collect.py)" = 3e5c5ce30d15f3741b45a4900a8341bc339a85c9
export MG03_COLLECTOR_ROOT="$RUNNER_TEMP/mg03/collector"
export PYTHONPATH="$RUNNER_TEMP/mg03/ygg-r12:$GITHUB_WORKSPACE/research/lcrm01"
echo MG03_YGG_ORIGINAL_R10_R11_R12_AND_INDEPENDENT_PUBLIC_COLLECTOR_VERIFIED

python -B research/lcrm01/mg03_equal_public_doorkey_live.py \
 --wingless-go-dk7 "$MG03_WINGLESS_DK7" \
 --output "$RUNNER_TEMP/mg03/first.json" > "$RUNNER_TEMP/mg03/first.log" 2>&1 || {
 cat "$RUNNER_TEMP/mg03/first.log"; exit 1;
}
cat "$RUNNER_TEMP/mg03/first.log"
python -B research/lcrm01/mg03_equal_public_doorkey_live.py \
 --wingless-go-dk7 "$MG03_WINGLESS_DK7" \
 --output "$RUNNER_TEMP/mg03/second.json" > "$RUNNER_TEMP/mg03/second.log" 2>&1 || {
 cat "$RUNNER_TEMP/mg03/second.log"; exit 1;
}
cat "$RUNNER_TEMP/mg03/second.log"
python -B research/lcrm01/mg03_compare.py \
 --a "$RUNNER_TEMP/mg03/first.json" \
 --b "$RUNNER_TEMP/mg03/second.json" \
 --output "$RUNNER_TEMP/mg03/comparison.json"
python - "$RUNNER_TEMP/mg03/comparison.json" <<'PY'
import json,sys
d=json.load(open(sys.argv[1]))
assert d["classification"]=="MG03_EQUAL_PUBLIC_SEVEN_ACTION_DOORKEY_NATIVE_INTERFACES_CONNECTED__NO_SCIENCE"
assert d["wingless_new_go_seven_action"] and not d["wingless_R8_upgraded"] and not d["scientific_first_use"]
print("MG03_TWO_NATIVE_SEVEN_ACTION_EQUAL_PUBLIC_SOURCE_PASS",d["canonical_sha256"])
PY
test -z "$(git status --porcelain --untracked-files=all)"
test -z "$(git -C "$RUNNER_TEMP/mg03/minigrid" status --porcelain --untracked-files=no)"
test -z "$(git -C "$RUNNER_TEMP/mg03/wingless" status --porcelain --untracked-files=no)"
test -z "$(git -C "$RUNNER_TEMP/mg03/ygg-r12" status --porcelain --untracked-files=no)"
test -z "$(git -C "$RUNNER_TEMP/mg03/collector" status --porcelain --untracked-files=no)"
echo MG03_ORIGINAL_FARAMA_PAIRED_SEVEN_ACTION_CONNECTED_NOT_SCIENCE
