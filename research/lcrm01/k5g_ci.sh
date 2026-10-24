#!/usr/bin/env bash
set -euo pipefail
cd "$GITHUB_WORKSPACE"
test "$(git rev-parse '1b88d61b961faca8c3a5a0e72a2a725c273401fa^')" = 'e5dc5a21c889dd7638cf8678a1b834c4793f7da2'
git merge-base --is-ancestor 1b88d61b961faca8c3a5a0e72a2a725c273401fa HEAD
test "$(git hash-object research/lcrm01/k5g_frozen_active_sensing.json)" = '13e079739e502e52055314a5ae385acb42bcc064'
test "$(git hash-object research/lcrm01/k5f_frozen_dynamic_obstacles.json)" = '40329f55c2f8a3867f4158cc46fe405a7939aea7'
echo 'K5G_PREREG_BEFORE_SOURCE_FIRST_USE=PASS'
python -B - <<'PY'
import ast,pathlib
for f in ("k5g_active_sensing.py","k5g_compare.py"):
 ast.parse((pathlib.Path("research/lcrm01")/f).read_text())
print("K5G_ORIGINAL_CODE_AST=PASS")
PY
mkdir -p "$RUNNER_TEMP/k5g"
python -m pip install 'pip==24.0' 'setuptools==69.5.1' 'wheel==0.43.0'
python -m pip install 'numpy==1.26.4' 'gymnasium==1.1.1' 'pygame-ce==2.5.3'
export PYTHONPATH="$GITHUB_WORKSPACE/research/lcrm01"
python -B -m unittest discover -s research/lcrm01 -p 'test_k5g_sourceonly.py' -v
git init -q "$RUNNER_TEMP/k5g/minigrid"
git -C "$RUNNER_TEMP/k5g/minigrid" remote add origin https://github.com/Farama-Foundation/Minigrid.git
git -C "$RUNNER_TEMP/k5g/minigrid" fetch --no-tags --depth 1 origin 7f5853792ea7f04f75614661006d87fcf949f26d
git -C "$RUNNER_TEMP/k5g/minigrid" checkout --detach -q 7f5853792ea7f04f75614661006d87fcf949f26d
for entry in \
 "minigrid/envs/dynamicobstacles.py:68436cecc35116c23c2f196c22fa3a19c6410b95" \
 "minigrid/envs/empty.py:8810bb0fa156d18475022edd8859b135ef745a5f" \
 "minigrid/envs/fourrooms.py:d79f007e00f95f48284da66d760872483c02fab2" \
 "minigrid/wrappers.py:1eb2da8fb612653c97f443ff6c7492ed3f1aaa80" \
 "minigrid/minigrid_env.py:eb29e9a902de0715ab77ec981a2113576d7664fa"; do
 path="${entry%%:*}";expected="${entry#*:}"
 test "$(git -C "$RUNNER_TEMP/k5g/minigrid" hash-object "$path")" = "$expected"
done
python -m pip install --no-deps -e "$RUNNER_TEMP/k5g/minigrid"
git init -q "$RUNNER_TEMP/k5g/Yggdrasil"
git -C "$RUNNER_TEMP/k5g/Yggdrasil" remote add origin https://github.com/spoonman136668-ai/Yggdrasil.git
git -C "$RUNNER_TEMP/k5g/Yggdrasil" fetch --no-tags --depth 1 origin fbf78bcc6988755ba0e3e026f06d273839c1fa9f
git -C "$RUNNER_TEMP/k5g/Yggdrasil" checkout --detach -q fbf78bcc6988755ba0e3e026f06d273839c1fa9f
test "$(git -C "$RUNNER_TEMP/k5g/Yggdrasil" hash-object research/native/itd02/r2/affordance_cells.py)" = 'f7e47dfef309e1c0bcc871d518154fd950b3eca0'
test "$(git -C "$RUNNER_TEMP/k5g/Yggdrasil" hash-object research/native/itd02/r3/navigator.py)" = '5348238f4ec2183bea29262659883391b5f429fd'
test "$(git -C "$RUNNER_TEMP/k5g/Yggdrasil" hash-object research/native/itd02/r3/PREREG.json)" = 'd518e5443d0d6462f8fa32fb41283c8a26aca2ad'
export PYTHONPATH="$RUNNER_TEMP/k5g/Yggdrasil:$GITHUB_WORKSPACE/research/lcrm01"
python -B -m unittest discover -s "$RUNNER_TEMP/k5g/Yggdrasil/research/native/itd02/r3" -p 'test_navigator.py' -v
echo 'K5G_PINNED_EXTERNAL_SOURCE_AND_ORIGINAL_NATIVE=PASS'
set +e
python -B research/lcrm01/k5g_active_sensing.py --output "$RUNNER_TEMP/k5g/process-a.json" > "$RUNNER_TEMP/k5g/process-a.log" 2>&1
a=$?
python -B research/lcrm01/k5g_active_sensing.py --output "$RUNNER_TEMP/k5g/process-b.json" > "$RUNNER_TEMP/k5g/process-b.log" 2>&1
b=$?
set -e
echo "K5G_PROCESS_A_EXIT=$a K5G_PROCESS_B_EXIT=$b"
cat "$RUNNER_TEMP/k5g/process-a.log" "$RUNNER_TEMP/k5g/process-b.log"
test "$a" -eq 0 && test "$b" -eq 0
python -B research/lcrm01/k5g_compare.py \
 --first "$RUNNER_TEMP/k5g/process-a.json" \
 --second "$RUNNER_TEMP/k5g/process-b.json" \
 --output "$RUNNER_TEMP/k5g/comparison.json"
test -z "$(git -C "$RUNNER_TEMP/k5g/minigrid" status --porcelain --untracked-files=no)"
test -z "$(git -C "$RUNNER_TEMP/k5g/Yggdrasil" status --porcelain --untracked-files=no)"
echo 'K5G_ACTUAL_BUDGETED_ORIGINAL_SOURCE_CUSTODY_PASS'
