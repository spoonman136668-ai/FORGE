#!/usr/bin/env bash
# K5E original authored causal micro-world, not external physical simulator.
set -euo pipefail
cd "$GITHUB_WORKSPACE"
test "$(git rev-parse 'f9242e5b6d6de075caec8bdfdd2ba541eae95569^')" = '7ce3c69ae8a8445256413318294e273f7dbf4d8a'
git merge-base --is-ancestor f9242e5b6d6de075caec8bdfdd2ba541eae95569 HEAD
test "$(git hash-object research/lcrm01/k5e_frozen_nonlinear.json)" = '2b2a2cabb2fb5e2b655fe37f23026fde4005c074'
test "$(git hash-object research/lcrm01/k5e_nonlinear_world.py)" = 'a43643ee6435f15e42cc671f54a6e401f7188a98'
test "$(git hash-object research/lcrm01/k5d_frozen_composition.json)" = 'd785aa5e2c5f957713e64b42ef19f9fa4b7f9350'
echo 'K5E_ORIGINAL_NONAFFINE_SOURCE_FROZEN=PASS'
python -B - <<'PY'
import ast,pathlib
for name in ("k5e_nonlinear_world.py","k5e_nonlinear_trial.py","k5e_compare.py"):
 ast.parse((pathlib.Path("research/lcrm01")/name).read_text())
print("K5E_PRE_FIRST_USE_AST=PASS")
PY
export PYTHONPATH="$GITHUB_WORKSPACE/research/lcrm01"
python -B -m unittest discover -s research/lcrm01 -p 'test_k5e_sourceonly.py' -v
mkdir -p "$RUNNER_TEMP/k5e"
git init -q "$RUNNER_TEMP/k5e/Yggdrasil"
git -C "$RUNNER_TEMP/k5e/Yggdrasil" remote add origin https://github.com/spoonman136668-ai/Yggdrasil.git
git -C "$RUNNER_TEMP/k5e/Yggdrasil" fetch --no-tags --depth 1 origin a509c23d8b0d0a11d3d5d38eaa70656c7ab07ddd
git -C "$RUNNER_TEMP/k5e/Yggdrasil" checkout --detach -q a509c23d8b0d0a11d3d5d38eaa70656c7ab07ddd
test "$(git -C "$RUNNER_TEMP/k5e/Yggdrasil" hash-object research/native/itd02/r7/learner.py)" = '204ecd993b954b23e66d6d1e8b3568e7c93183c5'
test "$(git -C "$RUNNER_TEMP/k5e/Yggdrasil" hash-object research/native/itd02/r7/PREREG.json)" = '90def4fb42537a214c8aaa6f3ac14b2858498de7'
test "$(git -C "$RUNNER_TEMP/k5e/Yggdrasil" hash-object research/native/itd02/r6/composer.py)" = '236386eab51461343d3c2103851ad1de110769a4'
export PYTHONPATH="$RUNNER_TEMP/k5e/Yggdrasil:$GITHUB_WORKSPACE/research/lcrm01"
python -B -m unittest discover -s "$RUNNER_TEMP/k5e/Yggdrasil/research/native/itd02/r7" -p 'test_learner.py' -v
echo 'K5E_ALL_SOURCE_OWNER_IDENTITIES=PASS'
set +e
python -B research/lcrm01/k5e_nonlinear_trial.py --output "$RUNNER_TEMP/k5e/process-a.json" > "$RUNNER_TEMP/k5e/process-a.log" 2>&1
a=$?
python -B research/lcrm01/k5e_nonlinear_trial.py --output "$RUNNER_TEMP/k5e/process-b.json" > "$RUNNER_TEMP/k5e/process-b.log" 2>&1
b=$?
set -e
echo "K5E_ORIGINAL_A_EXIT=$a K5E_ORIGINAL_B_EXIT=$b"
cat "$RUNNER_TEMP/k5e/process-a.log" "$RUNNER_TEMP/k5e/process-b.log"
test "$a" -eq 0 && test "$b" -eq 0
python -B research/lcrm01/k5e_compare.py --first "$RUNNER_TEMP/k5e/process-a.json" --second "$RUNNER_TEMP/k5e/process-b.json" --output "$RUNNER_TEMP/k5e/comparison.json"
test -z "$(git -C "$RUNNER_TEMP/k5e/Yggdrasil" status --porcelain --untracked-files=no)"
echo 'K5E_SOURCE_CAUSAL_COMPOSITION_ORIGINAL_SCIE_COMPLETE=PASS'
