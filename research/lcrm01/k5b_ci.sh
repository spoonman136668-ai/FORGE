#!/usr/bin/env bash
# K5B original public MemoryEnv physical task, no controller or FSA writes.
set -euo pipefail
cd "$GITHUB_WORKSPACE"
test "$(git rev-parse '4583d0aa295dc8e2b0d08ce2b85ab640e3831884^')" = 'f60b384416a473a0fff424d20d2efa29bf8d8dbf'
git merge-base --is-ancestor 4583d0aa295dc8e2b0d08ce2b85ab640e3831884 HEAD
test "$(git hash-object research/lcrm01/k5b_frozen_memory_task.json)" = '894f6e4668f3ec42bab097464dfb9d3582bd5b08'
test "$(git hash-object research/lcrm01/k5a_frozen_crossing_ablation.json)" = 'c56fae2e9bed195f264ace08c019842aa8575848'
echo "K5B_EARLY_SOURCE_FROZEN=PASS"
python -B - <<'PY'
import ast,pathlib
for f in ("k5b_memory_trial.py","k5b_compare.py"):
 ast.parse((pathlib.Path("research/lcrm01")/f).read_text())
print("K5B_SOURCE_AST=PASS")
PY
export PYTHONPATH="$GITHUB_WORKSPACE/research/lcrm01"
mkdir -p "$RUNNER_TEMP/k5b"
python -m pip install 'pip==24.0' 'setuptools==69.5.1' 'wheel==0.43.0'
python -m pip install 'numpy==1.26.4' 'gymnasium==1.1.1' 'pygame-ce==2.5.3'
python -B -m unittest discover -s research/lcrm01 -p 'test_k5b_sourceonly.py' -v
git init -q "$RUNNER_TEMP/k5b/minigrid"
git -C "$RUNNER_TEMP/k5b/minigrid" remote add origin https://github.com/Farama-Foundation/Minigrid.git
git -C "$RUNNER_TEMP/k5b/minigrid" fetch --no-tags --depth 1 origin 7f5853792ea7f04f75614661006d87fcf949f26d
git -C "$RUNNER_TEMP/k5b/minigrid" checkout --detach -q 7f5853792ea7f04f75614661006d87fcf949f26d
test "$(git -C "$RUNNER_TEMP/k5b/minigrid" hash-object minigrid/envs/memory.py)" = '660b0a1b769948034c87bb421759c2b9a4f24548'
test "$(git -C "$RUNNER_TEMP/k5b/minigrid" hash-object minigrid/wrappers.py)" = '1eb2da8fb612653c97f443ff6c7492ed3f1aaa80'
test "$(git -C "$RUNNER_TEMP/k5b/minigrid" hash-object minigrid/minigrid_env.py)" = 'eb29e9a902de0715ab77ec981a2113576d7664fa'
python -m pip install --no-deps -e "$RUNNER_TEMP/k5b/minigrid"
git init -q "$RUNNER_TEMP/k5b/Yggdrasil"
git -C "$RUNNER_TEMP/k5b/Yggdrasil" remote add origin https://github.com/spoonman136668-ai/Yggdrasil.git
git -C "$RUNNER_TEMP/k5b/Yggdrasil" fetch --no-tags --depth 1 origin 3d9b3e282533c92557e947a3c2d5271f671165f9
git -C "$RUNNER_TEMP/k5b/Yggdrasil" checkout --detach -q 3d9b3e282533c92557e947a3c2d5271f671165f9
test "$(git -C "$RUNNER_TEMP/k5b/Yggdrasil" hash-object research/native/itd02/r4/cue_cells.py)" = 'bb8747e225335affe0e23f57e3c5d692a25bf473'
test "$(git -C "$RUNNER_TEMP/k5b/Yggdrasil" hash-object research/native/itd02/r4/PREREG.json)" = '8be70e973bdbf9f1799e5fafd0e376da4bc83911'
export PYTHONPATH="$RUNNER_TEMP/k5b/Yggdrasil:$GITHUB_WORKSPACE/research/lcrm01"
python -B -m unittest discover -s "$RUNNER_TEMP/k5b/Yggdrasil/research/native/itd02/r4" -p 'test_cue_cells.py' -v
echo "K5B_PINNED_NATIVE_AND_MEMORY_ENV_AUTHENTIC=PASS"
# Before any holdout: original FIT must meet support & cold restore conditions.
set +e
python -B research/lcrm01/k5b_memory_trial.py --output "$RUNNER_TEMP/k5b/process-a.json" > "$RUNNER_TEMP/k5b/process-a.log" 2>&1
a=$?
python -B research/lcrm01/k5b_memory_trial.py --output "$RUNNER_TEMP/k5b/process-b.json" > "$RUNNER_TEMP/k5b/process-b.log" 2>&1
b=$?
set -e
echo "K5B_PROCESS_A_EXIT=$a K5B_PROCESS_B_EXIT=$b"
cat "$RUNNER_TEMP/k5b/process-a.log" "$RUNNER_TEMP/k5b/process-b.log"
test "$a" -eq 0 && test "$b" -eq 0
python -B research/lcrm01/k5b_compare.py --first "$RUNNER_TEMP/k5b/process-a.json" --second "$RUNNER_TEMP/k5b/process-b.json" --output "$RUNNER_TEMP/k5b/comparison.json"
test -z "$(git -C "$RUNNER_TEMP/k5b/minigrid" status --porcelain --untracked-files=no)"
test -z "$(git -C "$RUNNER_TEMP/k5b/Yggdrasil" status --porcelain --untracked-files=no)"
echo "K5B_SOURCE_ORIGINAL_SCIENCE_AUTHENTICATED=PASS"
