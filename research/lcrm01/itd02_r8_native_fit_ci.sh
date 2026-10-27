#!/usr/bin/env bash
# Original-world FIT only: pinned Wingless Go bridge + pinned MiniGrid source.
set -euo pipefail
cd "${GITHUB_WORKSPACE:?}"
ROOT="${RUNNER_TEMP:?}/itd02-r8-native-fit-source"
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
git -C "$ROOT/wingless" fetch --no-tags --depth 1 origin 9061b256b9d68e4d83b3a10e51fb8b7ef365259f
git -C "$ROOT/wingless" checkout -q --detach 9061b256b9d68e4d83b3a10e51fb8b7ef365259f
test "$(git -C "$ROOT/wingless" rev-parse HEAD)" = 9061b256b9d68e4d83b3a10e51fb8b7ef365259f
test "$(git -C "$ROOT/wingless" hash-object research/native/itd02/r8/online_beliefs.go)" = 6857ecbef2d63f459a432a5d68c7edda2b5347c4
cp research/lcrm01/itd02_r8_wingless_bridge.go "$ROOT/wingless/itd02_r8_bridge.go"
(cd "$ROOT/wingless" && go build -trimpath -o "$ROOT/wingless-r8" itd02_r8_bridge.go)
export ITD02_R8_BRIDGE="$ROOT/wingless-r8"
export PYTHONPATH="$PWD/research/lcrm01"
python -B research/lcrm01/itd02_r8_native_fit_only.py
