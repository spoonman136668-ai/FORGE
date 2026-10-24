#!/usr/bin/env bash
set -euo pipefail
cd "$GITHUB_WORKSPACE"
test "$(git rev-parse 'c76ba27279a0e900576b3299409c2c30a23dbd6a^')" = '61d023fd48a0701d2ef42c2752afae79bbdbfad9'
git merge-base --is-ancestor c76ba27279a0e900576b3299409c2c30a23dbd6a HEAD
test "$(git hash-object research/lcrm01/k5c_frozen_concurrent_memory.json)" = '3af7a71bab9a8854a2f23d445debf98bbb69ea69'
test "$(git hash-object research/lcrm01/k5b_frozen_memory_task.json)" = '894f6e4668f3ec42bab097464dfb9d3582bd5b08'
echo 'K5C_FROZEN_BEFORE_ANY_NEW_TASK=PASS'
python -B - <<'PY'
import ast,pathlib
for name in ("k5c_concurrent_memory_trial.py","k5c_compare.py"):
 ast.parse((pathlib.Path("research/lcrm01")/name).read_text())
print("K5C_PREPHYSICS_PYTHON_AST=PASS")
PY
mkdir -p "$RUNNER_TEMP/k5c"
python -m pip install 'pip==24.0' 'setuptools==69.5.1' 'wheel==0.43.0'
python -m pip install 'numpy==1.26.4' 'gymnasium==1.1.1' 'pygame-ce==2.5.3'
export PYTHONPATH="$GITHUB_WORKSPACE/research/lcrm01"
python -B -m unittest discover -s research/lcrm01 -p 'test_k5c_sourceonly.py' -v
git init -q "$RUNNER_TEMP/k5c/minigrid"
git -C "$RUNNER_TEMP/k5c/minigrid" remote add origin https://github.com/Farama-Foundation/Minigrid.git
git -C "$RUNNER_TEMP/k5c/minigrid" fetch --no-tags --depth 1 origin 7f5853792ea7f04f75614661006d87fcf949f26d
git -C "$RUNNER_TEMP/k5c/minigrid" checkout --detach -q 7f5853792ea7f04f75614661006d87fcf949f26d
test "$(git -C "$RUNNER_TEMP/k5c/minigrid" hash-object minigrid/envs/memory.py)" = '660b0a1b769948034c87bb421759c2b9a4f24548'
test "$(git -C "$RUNNER_TEMP/k5c/minigrid" hash-object minigrid/wrappers.py)" = '1eb2da8fb612653c97f443ff6c7492ed3f1aaa80'
test "$(git -C "$RUNNER_TEMP/k5c/minigrid" hash-object minigrid/minigrid_env.py)" = 'eb29e9a902de0715ab77ec981a2113576d7664fa'
python -m pip install --no-deps -e "$RUNNER_TEMP/k5c/minigrid"
git init -q "$RUNNER_TEMP/k5c/Yggdrasil"
git -C "$RUNNER_TEMP/k5c/Yggdrasil" remote add origin https://github.com/spoonman136668-ai/Yggdrasil.git
git -C "$RUNNER_TEMP/k5c/Yggdrasil" fetch --no-tags --depth 1 origin 6f9cb5c80f278eab15f73a7a121dc4fa1f331b92
git -C "$RUNNER_TEMP/k5c/Yggdrasil" checkout --detach -q 6f9cb5c80f278eab15f73a7a121dc4fa1f331b92
test "$(git -C "$RUNNER_TEMP/k5c/Yggdrasil" hash-object research/native/itd02/r5/concurrent_cues.py)" = '4182889a47e31391a95ea3a2f5d8a4b87bcd6359'
test "$(git -C "$RUNNER_TEMP/k5c/Yggdrasil" hash-object research/native/itd02/r5/PREREG.json)" = '758a1c537b911a0d12d9a18becf2fe462c666480'
test "$(git -C "$RUNNER_TEMP/k5c/Yggdrasil" hash-object research/native/itd02/r4/cue_cells.py)" = 'bb8747e225335affe0e23f57e3c5d692a25bf473'
export PYTHONPATH="$RUNNER_TEMP/k5c/Yggdrasil:$GITHUB_WORKSPACE/research/lcrm01"
python -B -m unittest discover -s "$RUNNER_TEMP/k5c/Yggdrasil/research/native/itd02/r5" -p 'test_concurrent_cues.py' -v
echo 'K5C_SOURCE_OWNED_NATIVE_AND_ORIGINAL_MINIGRID_AUTHENTIC=PASS'
set +e
python -B research/lcrm01/k5c_concurrent_memory_trial.py --output "$RUNNER_TEMP/k5c/process-a.json" > "$RUNNER_TEMP/k5c/process-a.log" 2>&1
a=$?
python -B research/lcrm01/k5c_concurrent_memory_trial.py --output "$RUNNER_TEMP/k5c/process-b.json" > "$RUNNER_TEMP/k5c/process-b.log" 2>&1
b=$?
set -e
echo "K5C_PROCESS_A_EXIT=$a K5C_PROCESS_B_EXIT=$b"
cat "$RUNNER_TEMP/k5c/process-a.log" "$RUNNER_TEMP/k5c/process-b.log"
test "$a" -eq 0 && test "$b" -eq 0
python -B research/lcrm01/k5c_compare.py --first "$RUNNER_TEMP/k5c/process-a.json" --second "$RUNNER_TEMP/k5c/process-b.json" --output "$RUNNER_TEMP/k5c/comparison.json"
test -z "$(git -C "$RUNNER_TEMP/k5c/minigrid" status --porcelain --untracked-files=no)"
test -z "$(git -C "$RUNNER_TEMP/k5c/Yggdrasil" status --porcelain --untracked-files=no)"
echo 'K5C_PRESERVED_ORIGINAL_REPORTS_AND_SOURCE_GATE=PASS'
