#!/usr/bin/env bash
set -euo pipefail
cd "$GITHUB_WORKSPACE"
ROOT="$RUNNER_TEMP/itd02-r8-bridge"
mkdir -p "$ROOT"
git init -q "$ROOT/wingless"
git -C "$ROOT/wingless" remote add origin https://github.com/spoonman136668-ai/Wingless.git
git -C "$ROOT/wingless" fetch --no-tags --depth 1 origin 9061b256b9d68e4d83b3a10e51fb8b7ef365259f
git -C "$ROOT/wingless" checkout -q --detach 9061b256b9d68e4d83b3a10e51fb8b7ef365259f
test "$(git -C "$ROOT/wingless" rev-parse HEAD)" = 9061b256b9d68e4d83b3a10e51fb8b7ef365259f
test "$(git -C "$ROOT/wingless" hash-object research/native/itd02/r8/online_beliefs.go)" = 6857ecbef2d63f459a432a5d68c7edda2b5347c4
(cd "$ROOT/wingless" && go test -count=1 ./research/native/itd02/r8 && go vet ./research/native/itd02/r8)
cp research/lcrm01/itd02_r8_wingless_bridge.go "$ROOT/wingless/itd02_r8_bridge.go"
(cd "$ROOT/wingless" && go build -trimpath -o "$ROOT/wingless-r8" itd02_r8_bridge.go)
export ITD02_R8_BRIDGE="$ROOT/wingless-r8"
python -B -m unittest discover -s research/lcrm01 -p test_itd02_r8_bridge.py -v
python -B -m unittest discover -s research/lcrm01 -p test_itd02_r8_episode_contract.py -v
python -B research/lcrm01/itd02_r8_original_world_preflight.py
python -B -m unittest discover -s research/lcrm01 -p test_itd02_r8_original_episode.py -v
python -B -m unittest discover -s research/lcrm01 -p test_itd02_r8_comparator_gate.py -v
python -B -m unittest discover -s research/lcrm01 -p test_itd02_r8_conditional_beta.py -v
python -B -m unittest discover -s research/lcrm01 -p test_itd02_r8_previous_action_ablation.py -v
python -B -m unittest discover -s research/lcrm01 -p test_itd02_r8_statistical_episode.py -v
echo ITD02_R8_PINNED_NATIVE_BRIDGE_FOCUSED_PASS
