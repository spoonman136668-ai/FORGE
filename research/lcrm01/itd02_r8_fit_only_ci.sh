#!/usr/bin/env bash
# Explicit FIT-only runner; not invoked by focused source-only CI.
set -euo pipefail
cd "${GITHUB_WORKSPACE:?}"
export PYTHONPATH="$PWD/research/lcrm01"
ROOT="${RUNNER_TEMP:?}/itd02-r8-fit"
mkdir -p "$ROOT"
python -m pip install 'numpy==1.26.4' 'gymnasium==1.1.1' 'pygame-ce==2.5.3'
git init -q "$ROOT/minigrid"
git -C "$ROOT/minigrid" remote add origin https://github.com/Farama-Foundation/Minigrid.git
git -C "$ROOT/minigrid" fetch --no-tags --depth 1 origin 7f5853792ea7f04f75614661006d87fcf949f26d
git -C "$ROOT/minigrid" checkout -q --detach 7f5853792ea7f04f75614661006d87fcf949f26d
test "$(git -C "$ROOT/minigrid" hash-object minigrid/envs/empty.py)" = 8810bb0fa156d18475022edd8859b135ef745a5f
test "$(git -C "$ROOT/minigrid" hash-object minigrid/envs/fourrooms.py)" = d79f007e00f95f48284da66d760872483c02fab2
python -m pip install --no-deps -e "$ROOT/minigrid"
python -B research/lcrm01/itd02_r8_fit_only_run.py | tee "$ROOT/fit-receipt.json"
