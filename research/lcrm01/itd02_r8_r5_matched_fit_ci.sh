#!/usr/bin/env bash
# Matched R5 source-only FIT execution. No CHECK or DEV environment use.
set -euo pipefail
cd "${GITHUB_WORKSPACE:?}"
ROOT="${RUNNER_TEMP:?}/itd02-r5-matched-fit-source"
mkdir -p "$ROOT"
python -m pip install 'numpy==1.26.4' 'gymnasium==1.1.1' 'pygame-ce==2.5.3'
git init -q "$ROOT/minigrid"
git -C "$ROOT/minigrid" remote add origin https://github.com/Farama-Foundation/Minigrid.git
git -C "$ROOT/minigrid" fetch --no-tags --depth 1 origin 7f5853792ea7f04f75614661006d87fcf949f26d
git -C "$ROOT/minigrid" checkout -q --detach 7f5853792ea7f04f75614661006d87fcf949f26d
test "$(git -C "$ROOT/minigrid" rev-parse HEAD)" = 7f5853792ea7f04f75614661006d87fcf949f26d
test "$(git -C "$ROOT/minigrid" hash-object minigrid/envs/empty.py)" = 8810bb0fa156d18475022edd8859b135ef745a5f
test "$(git -C "$ROOT/minigrid" hash-object minigrid/envs/fourrooms.py)" = d79f007e00f95f48284da66d760872483c02fab2
python -m pip install --no-deps -e "$ROOT/minigrid"
git init -q "$ROOT/wingless"
git -C "$ROOT/wingless" remote add origin https://github.com/spoonman136668-ai/Wingless.git
git -C "$ROOT/wingless" fetch --no-tags --depth 1 origin 978825064dd6076058a1a38ae1a9a3d80e28d99e
git -C "$ROOT/wingless" checkout -q --detach 978825064dd6076058a1a38ae1a9a3d80e28d99e
test "$(git -C "$ROOT/wingless" rev-parse HEAD)" = 978825064dd6076058a1a38ae1a9a3d80e28d99e
test "$(git -C "$ROOT/wingless" hash-object research/native/itd02/r5/cost_frontier.go)" = 239a5f2ab6d122b10cd5c7cc9388d154929b9888
cp research/lcrm01/itd02_r8_original_r5_bridge.go "$ROOT/wingless/r5_ipc.go"
(cd "$ROOT/wingless" && go build -trimpath -o "$ROOT/r5-native-bridge" r5_ipc.go)
export ITD02_R5_BRIDGE="$ROOT/r5-native-bridge"
export PYTHONPATH="$PWD/research/lcrm01"
python -B research/lcrm01/itd02_r8_r5_matched_fit.py
