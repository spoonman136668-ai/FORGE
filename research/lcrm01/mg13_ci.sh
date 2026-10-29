#!/usr/bin/env bash
# Source-only MG13, original Farama and independent Go/Ygg/conventional.
set -euo pipefail
cd "$GITHUB_WORKSPACE"
export PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 PIP_DISABLE_PIP_VERSION_CHECK=1
git merge-base --is-ancestor 0ec12ea47f4ca7db279b3d50fb18ad8ec3735b11 "$GITHUB_SHA"
git merge-base --is-ancestor 87c717002a0d25331c657b20efb1b8f25a8f0e5a "$GITHUB_SHA"
git merge-base --is-ancestor bf11b3d12f4ec5aba6d00f0f539aa03bbaf60efd "$GITHUB_SHA"
git merge-base --is-ancestor 01edaeb460ffb84e103d2aa5f67cc265bdd65d25 "$GITHUB_SHA"
git merge-base --is-ancestor ecbdc51b7794f6fe69f8f026a4c3c542d0f69fde "$GITHUB_SHA"
test "$(git hash-object research/lcrm01/mg11_authentic_selected_novelty.py)" = 89f68a4f97232cd63cdbb2675e1deb53d75abfcb
test "$(git hash-object research/lcrm01/mg12_conventional_two_step.py)" = 6b5e89c69700a5e4c730e415567ea8d4419c0cc8
test -z "$(git status --porcelain --untracked-files=all)"
echo MG13_PREREG_SOURCE_AND_OLD_GATES_FROZEN_PASS
mkdir -p "$RUNNER_TEMP/mg13/farama" "$RUNNER_TEMP/mg13/wingless" "$RUNNER_TEMP/mg13/yggdrasil" "$RUNNER_TEMP/mg13/collector"
python -m pip install 'pip==24.0' 'setuptools==69.5.1' 'wheel==0.43.0'
python -m pip install 'numpy==1.26.4' 'gymnasium==1.1.1' 'pygame-ce==2.5.3'

git init -q "$RUNNER_TEMP/mg13/farama"
git -C "$RUNNER_TEMP/mg13/farama" remote add origin https://github.com/Farama-Foundation/Minigrid.git
git -C "$RUNNER_TEMP/mg13/farama" fetch --no-tags --depth 1 origin 7f5853792ea7f04f75614661006d87fcf949f26d
git -C "$RUNNER_TEMP/mg13/farama" checkout --detach -q 7f5853792ea7f04f75614661006d87fcf949f26d
test "$(git -C "$RUNNER_TEMP/mg13/farama" hash-object minigrid/envs/doorkey.py)" = df5b29ef063be34e6d83b8b478e092c6e3e01512
test "$(git -C "$RUNNER_TEMP/mg13/farama" hash-object minigrid/wrappers.py)" = 1eb2da8fb612653c97f443ff6c7492ed3f1aaa80
python -m pip install --no-deps -e "$RUNNER_TEMP/mg13/farama"
echo MG13_AUTHENTIC_ORIGINAL_FARAMA_SOURCE_PINS_PASS

git init -q "$RUNNER_TEMP/mg13/wingless"
git -C "$RUNNER_TEMP/mg13/wingless" remote add origin https://github.com/spoonman136668-ai/Wingless.git
git -C "$RUNNER_TEMP/mg13/wingless" fetch --no-tags --depth 1 origin 1b5b3ed525c8905252b0919790e79c632b82c1e1
git -C "$RUNNER_TEMP/mg13/wingless" checkout --detach -q 1b5b3ed525c8905252b0919790e79c632b82c1e1
test "$(git -C "$RUNNER_TEMP/mg13/wingless" hash-object research/native/itd02/dk12/public_novelty.go)" = 117bbcc6d23f99cf2f89ba74c77e0e981b95ca94
test "$(git -C "$RUNNER_TEMP/mg13/wingless" hash-object research/native/itd02/dk12bridge/main.go)" = aa8ef4652e6911d1ba144e9ce0f9af1e03238f5d
test "$(git -C "$RUNNER_TEMP/mg13/wingless" hash-object research/native/itd02/dk11/continuity.go)" = 228027db110c3924aebf63420ff2caed47fe8c73
test "$(git -C "$RUNNER_TEMP/mg13/wingless" hash-object research/native/itd02/dk11bridge/main.go)" = 2b52a699859c12db2be51698ce3567dfa98413eb
test "$(git -C "$RUNNER_TEMP/mg13/wingless" hash-object research/native/itd02/dk10/temporal_policy.go)" = 3575ca351467ffd6200d277acf72b0d78dd54a52
test "$(git -C "$RUNNER_TEMP/mg13/wingless" hash-object research/native/itd02/r8/online_beliefs.go)" = 6857ecbef2d63f459a432a5d68c7edda2b5347c4
(cd "$RUNNER_TEMP/mg13/wingless" && go test -count=1 ./research/native/itd02/dk12/... ./research/native/itd02/dk11/... && go build -trimpath -o "$RUNNER_TEMP/mg13/dk12-go" ./research/native/itd02/dk12bridge && go build -trimpath -o "$RUNNER_TEMP/mg13/dk11-go" ./research/native/itd02/dk11bridge)
echo MG13_GO_NATIVE_DK11_NO_STAGE_SOURCE_QUALIFIED

git init -q "$RUNNER_TEMP/mg13/yggdrasil"
git -C "$RUNNER_TEMP/mg13/yggdrasil" remote add origin https://github.com/spoonman136668-ai/Yggdrasil.git
git -C "$RUNNER_TEMP/mg13/yggdrasil" fetch --no-tags --depth 1 origin 63dff5d870e158d4197ef39cf86d9339d3eccc16
git -C "$RUNNER_TEMP/mg13/yggdrasil" checkout --detach -q 63dff5d870e158d4197ef39cf86d9339d3eccc16
test "$(git -C "$RUNNER_TEMP/mg13/yggdrasil" hash-object research/native/itd02/r16/selected_novelty.py)" = 6718c9aeb5485992822102926fecc20fdf2aaa0b
test "$(git -C "$RUNNER_TEMP/mg13/yggdrasil" hash-object research/native/itd02/r15/continuity_cells.py)" = 6b31f4b0c301564b2793bef8a296a4e722825f01
test "$(git -C "$RUNNER_TEMP/mg13/yggdrasil" hash-object research/native/itd02/r14/temporal_cells.py)" = 8cacaad50e8d484f72da5067ff1f03c187877f27
test "$(git -C "$RUNNER_TEMP/mg13/yggdrasil" hash-object research/native/itd02/r11/affordance_cells.py)" = 614c7dfb1b43f485009b70cb85e9b7b5119cafc2
test "$(git -C "$RUNNER_TEMP/mg13/yggdrasil" hash-object research/native/itd02/r10/public_adapter.py)" = 3917d36ce9f86a2c1b998a0a2f93fb27674a9205
echo MG13_YGG_NATIVE_R15_LOCAL_CELL_SOURCE_QUALIFIED

git init -q "$RUNNER_TEMP/mg13/collector"
git -C "$RUNNER_TEMP/mg13/collector" remote add origin https://github.com/spoonman136668-ai/Yggdrasil.git
git -C "$RUNNER_TEMP/mg13/collector" fetch --no-tags --depth 1 origin 9d18cd04e7264898a92e4e382da6fac4398ad584
git -C "$RUNNER_TEMP/mg13/collector" checkout --detach -q 9d18cd04e7264898a92e4e382da6fac4398ad584
test "$(git -C "$RUNNER_TEMP/mg13/collector" hash-object research/mass_r7c29/collect.py)" = 3e5c5ce30d15f3741b45a4900a8341bc339a85c9
test "$(git -C "$RUNNER_TEMP/mg13/collector" hash-object research/mass_r7c30/control.py)" = c3183c8b8e43ef0e3531df964c80f0370fbc4914
export MG03_COLLECTOR_ROOT="$RUNNER_TEMP/mg13/collector"
export PYTHONPATH="$RUNNER_TEMP/mg13/yggdrasil:$GITHUB_WORKSPACE/research/lcrm01"
echo MG13_TRUE_INDEPENDENT_CONVENTIONAL_SOURCE_PINS_PASS

python -B research/lcrm01/mg13_authentic_postopen_fork.py \
 --wingless-dk12 "$RUNNER_TEMP/mg13/dk12-go" --wingless-dk11 "$RUNNER_TEMP/mg13/dk11-go" \
 --output "$RUNNER_TEMP/mg13/first.json" > "$RUNNER_TEMP/mg13/first.log" 2>&1 || {
 cat "$RUNNER_TEMP/mg13/first.log"; exit 1;
}
cat "$RUNNER_TEMP/mg13/first.log"
python -B research/lcrm01/mg13_authentic_postopen_fork.py \
 --wingless-dk12 "$RUNNER_TEMP/mg13/dk12-go" --wingless-dk11 "$RUNNER_TEMP/mg13/dk11-go" \
 --output "$RUNNER_TEMP/mg13/second.json" > "$RUNNER_TEMP/mg13/second.log" 2>&1 || {
 cat "$RUNNER_TEMP/mg13/second.log"; exit 1;
}
cat "$RUNNER_TEMP/mg13/second.log"
python -B research/lcrm01/mg13_compare.py \
 --first "$RUNNER_TEMP/mg13/first.json" \
 --second "$RUNNER_TEMP/mg13/second.json" \
 --output "$RUNNER_TEMP/mg13/comparison.json"
test -z "$(git status --porcelain --untracked-files=all)"
echo MG13_FORK_REPLAY_VERIFIED_PUBLIC_NATIVE_AND_CONVENTIONAL_SOURCE_QUALIFIED_NO_SCIENCE
