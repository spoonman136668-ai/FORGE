#!/usr/bin/env bash
set -euo pipefail
cd "$GITHUB_WORKSPACE"
test "$(git rev-parse 'd56400bd2f8969f09a8df7e78a8b876c55388bc4^')" = 'ee99cf0a2f91c032b57e86a896504a041f162cf0'
git merge-base --is-ancestor d56400bd2f8969f09a8df7e78a8b876c55388bc4 HEAD
test "$(git hash-object research/lcrm01/k5f_frozen_dynamic_obstacles.json)" = '40329f55c2f8a3867f4158cc46fe405a7939aea7'
test "$(git hash-object research/lcrm01/k5e_frozen_nonlinear.json)" = '2b2a2cabb2fb5e2b655fe37f23026fde4005c074'
python -B - <<'PY'
import ast,pathlib
for f in ("k5f_dynamic_obstacles.py","k5f_compare.py"):
 ast.parse((pathlib.Path("research/lcrm01")/f).read_text())
print("K5F_FROZEN_AND_AST=PASS")
PY
mkdir -p "$RUNNER_TEMP/k5f"
python -m pip install 'pip==24.0' 'setuptools==69.5.1' 'wheel==0.43.0'
python -m pip install 'numpy==1.26.4' 'gymnasium==1.1.1' 'pygame-ce==2.5.3'
export PYTHONPATH="$GITHUB_WORKSPACE/research/lcrm01"
python -B -m unittest discover -s research/lcrm01 -p 'test_k5f_sourceonly.py' -v
git init -q "$RUNNER_TEMP/k5f/minigrid"
git -C "$RUNNER_TEMP/k5f/minigrid" remote add origin https://github.com/Farama-Foundation/Minigrid.git
git -C "$RUNNER_TEMP/k5f/minigrid" fetch --no-tags --depth 1 origin 7f5853792ea7f04f75614661006d87fcf949f26d
git -C "$RUNNER_TEMP/k5f/minigrid" checkout --detach -q 7f5853792ea7f04f75614661006d87fcf949f26d
for entry in \
 "minigrid/envs/dynamicobstacles.py:68436cecc35116c23c2f196c22fa3a19c6410b95" \
 "minigrid/envs/empty.py:8810bb0fa156d18475022edd8859b135ef745a5f" \
 "minigrid/envs/fourrooms.py:d79f007e00f95f48284da66d760872483c02fab2" \
 "minigrid/wrappers.py:1eb2da8fb612653c97f443ff6c7492ed3f1aaa80" \
 "minigrid/minigrid_env.py:eb29e9a902de0715ab77ec981a2113576d7664fa"; do
 path="${entry%%:*}";expected="${entry#*:}"
 test "$(git -C "$RUNNER_TEMP/k5f/minigrid" hash-object "$path")" = "$expected"
done
python -m pip install --no-deps -e "$RUNNER_TEMP/k5f/minigrid"
git init -q "$RUNNER_TEMP/k5f/Yggdrasil"
git -C "$RUNNER_TEMP/k5f/Yggdrasil" remote add origin https://github.com/spoonman136668-ai/Yggdrasil.git
git -C "$RUNNER_TEMP/k5f/Yggdrasil" fetch --no-tags --depth 1 origin fbf78bcc6988755ba0e3e026f06d273839c1fa9f
git -C "$RUNNER_TEMP/k5f/Yggdrasil" checkout --detach -q fbf78bcc6988755ba0e3e026f06d273839c1fa9f
test "$(git -C "$RUNNER_TEMP/k5f/Yggdrasil" hash-object research/native/itd02/r2/affordance_cells.py)" = 'f7e47dfef309e1c0bcc871d518154fd950b3eca0'
test "$(git -C "$RUNNER_TEMP/k5f/Yggdrasil" hash-object research/native/itd02/r3/navigator.py)" = '5348238f4ec2183bea29262659883391b5f429fd'
test "$(git -C "$RUNNER_TEMP/k5f/Yggdrasil" hash-object research/native/itd02/r3/PREREG.json)" = 'd518e5443d0d6462f8fa32fb41283c8a26aca2ad'
export PYTHONPATH="$RUNNER_TEMP/k5f/Yggdrasil:$GITHUB_WORKSPACE/research/lcrm01"
python -B -m unittest discover -s "$RUNNER_TEMP/k5f/Yggdrasil/research/native/itd02/r3" -p 'test_navigator.py' -v
echo 'K5F_ORIGINAL_NATIVE_AND_DYNAMIC_SOURCE_AUTHENTIC=PASS'
set +e
python -B research/lcrm01/k5f_dynamic_obstacles.py --output "$RUNNER_TEMP/k5f/process-a.json" > "$RUNNER_TEMP/k5f/process-a.log" 2>&1
a=$?
python -B research/lcrm01/k5f_dynamic_obstacles.py --output "$RUNNER_TEMP/k5f/process-b.json" > "$RUNNER_TEMP/k5f/process-b.log" 2>&1
b=$?
set -e
echo "K5F_PROCESS_A_EXIT=$a K5F_PROCESS_B_EXIT=$b"
cat "$RUNNER_TEMP/k5f/process-a.log" "$RUNNER_TEMP/k5f/process-b.log"
test "$a" -eq 0 && test "$b" -eq 0
python -B research/lcrm01/k5f_compare.py \
 --first "$RUNNER_TEMP/k5f/process-a.json" \
 --second "$RUNNER_TEMP/k5f/process-b.json" \
 --output "$RUNNER_TEMP/k5f/comparison.json"
test -z "$(git -C "$RUNNER_TEMP/k5f/minigrid" status --porcelain --untracked-files=no)"
test -z "$(git -C "$RUNNER_TEMP/k5f/Yggdrasil" status --porcelain --untracked-files=no)"
echo 'K5F_AUTHENTIC_NONSTATIONARY_SOURCE_CUSTODY=PASS'
