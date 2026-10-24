#!/usr/bin/env bash
# Public-development only. No FORGE owner/controller or FSA writer mutation.
set -euo pipefail
cd "$GITHUB_WORKSPACE"
test "$(git rev-parse 'c3dff38903dbfcce32a54440d2cbdd775c597479^')" = '51f83d97e982264f2cad905e80742eb790e40464'
git merge-base --is-ancestor c3dff38903dbfcce32a54440d2cbdd775c597479 HEAD
test "$(git hash-object research/lcrm01/k5a_frozen_crossing_ablation.json)" = 'c56fae2e9bed195f264ace08c019842aa8575848'
test "$(git hash-object research/lcrm01/k4z_frozen_episodic_nav.json)" = 'ccfcbadc55570a13701cee8175290700e9f14865'
echo 'K5A_FROZEN_FIRST_USE_SOURCE=PASS'
python -B - <<'PY'
import ast,pathlib
for s in ("k5a_crossing_transfer.py","k5a_compare.py"):
 ast.parse((pathlib.Path("research/lcrm01")/s).read_text())
print("K5A_PYTHON_AST=PASS")
PY
export PYTHONPATH="$GITHUB_WORKSPACE/research/lcrm01"
python -B -m unittest discover -s research/lcrm01 -p 'test_k5a_sourceonly.py' -v
mkdir -p "$RUNNER_TEMP/k5a"
python -m pip install 'pip==24.0' 'setuptools==69.5.1' 'wheel==0.43.0'
python -m pip install 'numpy==1.26.4' 'gymnasium==1.1.1' 'pygame-ce==2.5.3'
git init -q "$RUNNER_TEMP/k5a/minigrid"
git -C "$RUNNER_TEMP/k5a/minigrid" remote add origin https://github.com/Farama-Foundation/Minigrid.git
git -C "$RUNNER_TEMP/k5a/minigrid" fetch --no-tags --depth 1 origin 7f5853792ea7f04f75614661006d87fcf949f26d
git -C "$RUNNER_TEMP/k5a/minigrid" checkout --detach -q 7f5853792ea7f04f75614661006d87fcf949f26d
for entry in \
 "minigrid/envs/crossing.py:f8c331e5e0e56b3b2a4a3b44dda8533bdabf4272" \
 "minigrid/envs/empty.py:8810bb0fa156d18475022edd8859b135ef745a5f" \
 "minigrid/envs/fourrooms.py:d79f007e00f95f48284da66d760872483c02fab2" \
 "minigrid/wrappers.py:1eb2da8fb612653c97f443ff6c7492ed3f1aaa80" \
 "minigrid/minigrid_env.py:eb29e9a902de0715ab77ec981a2113576d7664fa"; do
 path="${entry%%:*}";expected="${entry#*:}"
 test "$(git -C "$RUNNER_TEMP/k5a/minigrid" hash-object "$path")" = "$expected"
done
python -m pip install --no-deps -e "$RUNNER_TEMP/k5a/minigrid"
git init -q "$RUNNER_TEMP/k5a/Yggdrasil"
git -C "$RUNNER_TEMP/k5a/Yggdrasil" remote add origin https://github.com/spoonman136668-ai/Yggdrasil.git
git -C "$RUNNER_TEMP/k5a/Yggdrasil" fetch --no-tags --depth 1 origin fbf78bcc6988755ba0e3e026f06d273839c1fa9f
git -C "$RUNNER_TEMP/k5a/Yggdrasil" checkout --detach -q fbf78bcc6988755ba0e3e026f06d273839c1fa9f
test "$(git -C "$RUNNER_TEMP/k5a/Yggdrasil" hash-object research/native/itd02/r2/affordance_cells.py)" = 'f7e47dfef309e1c0bcc871d518154fd950b3eca0'
test "$(git -C "$RUNNER_TEMP/k5a/Yggdrasil" hash-object research/native/itd02/r3/navigator.py)" = '5348238f4ec2183bea29262659883391b5f429fd'
test "$(git -C "$RUNNER_TEMP/k5a/Yggdrasil" hash-object research/native/itd02/r3/PREREG.json)" = 'd518e5443d0d6462f8fa32fb41283c8a26aca2ad'
export PYTHONPATH="$RUNNER_TEMP/k5a/Yggdrasil:$GITHUB_WORKSPACE/research/lcrm01"
python -B -m unittest discover -s "$RUNNER_TEMP/k5a/Yggdrasil/research/native/itd02/r3" -p 'test_navigator.py' -v
echo 'K5A_AUTHENTIC_UNCHANGED_SOURCES_READY=PASS'
set +e
python -B research/lcrm01/k5a_crossing_transfer.py --output "$RUNNER_TEMP/k5a/process-a.json" > "$RUNNER_TEMP/k5a/process-a.log" 2>&1
a=$?
python -B research/lcrm01/k5a_crossing_transfer.py --output "$RUNNER_TEMP/k5a/process-b.json" > "$RUNNER_TEMP/k5a/process-b.log" 2>&1
b=$?
set -e
echo "K5A_PROCESS_A_EXIT=$a K5A_PROCESS_B_EXIT=$b"
cat "$RUNNER_TEMP/k5a/process-a.log" "$RUNNER_TEMP/k5a/process-b.log"
test "$a" -eq 0 && test "$b" -eq 0
python -B research/lcrm01/k5a_compare.py \
 --first "$RUNNER_TEMP/k5a/process-a.json" \
 --second "$RUNNER_TEMP/k5a/process-b.json" \
 --output "$RUNNER_TEMP/k5a/comparison.json"
test -z "$(git -C "$RUNNER_TEMP/k5a/minigrid" status --porcelain --untracked-files=no)"
test -z "$(git -C "$RUNNER_TEMP/k5a/Yggdrasil" status --porcelain --untracked-files=no)"
echo "K5A_UNFAMILIAR_SOURCE_GATES_PASSED"
