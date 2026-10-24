#!/usr/bin/env bash
set -euo pipefail
cd "$GITHUB_WORKSPACE"
test "$(git rev-parse '2b9997188e447dd1432e3217dc1ea2282730719d^')" = '15e18aef3a271c675dd7007fbdb8d869bfc682da'
git merge-base --is-ancestor 2b9997188e447dd1432e3217dc1ea2282730719d HEAD
test "$(git hash-object research/lcrm01/k5d_frozen_composition.json)" = 'd785aa5e2c5f957713e64b42ef19f9fa4b7f9350'
test "$(git hash-object research/lcrm01/k5d_causal_world.py)" = '1051f3e8a223fe20da51054a2f7ac2f3f74799cd'
test "$(git hash-object research/lcrm01/k5c_frozen_concurrent_memory.json)" = '3af7a71bab9a8854a2f23d445debf98bbb69ea69'
echo "K5D_FROZEN_CONSTRUCTED_WORLD_SOURCE=PASS"
python -B - <<'PY'
import ast,pathlib
for name in ("k5d_causal_world.py","k5d_causal_trial.py","k5d_compare.py"):
 ast.parse((pathlib.Path("research/lcrm01")/name).read_text())
print("K5D_ORIGINAL_AST_PREHELDOUT=PASS")
PY
export PYTHONPATH="$GITHUB_WORKSPACE/research/lcrm01"
python -B -m unittest discover -s research/lcrm01 -p 'test_k5d_sourceonly.py' -v
mkdir -p "$RUNNER_TEMP/k5d"
git init -q "$RUNNER_TEMP/k5d/Yggdrasil"
git -C "$RUNNER_TEMP/k5d/Yggdrasil" remote add origin https://github.com/spoonman136668-ai/Yggdrasil.git
git -C "$RUNNER_TEMP/k5d/Yggdrasil" fetch --no-tags --depth 1 origin 5fcfa67f041658d34040e05bc0141ce05092c30b
git -C "$RUNNER_TEMP/k5d/Yggdrasil" checkout --detach -q 5fcfa67f041658d34040e05bc0141ce05092c30b
test "$(git -C "$RUNNER_TEMP/k5d/Yggdrasil" hash-object research/native/itd02/r6/composer.py)" = '236386eab51461343d3c2103851ad1de110769a4'
test "$(git -C "$RUNNER_TEMP/k5d/Yggdrasil" hash-object research/native/itd02/r6/PREREG.json)" = 'ab10ce217dd777e3d6f8ef0b1577f91b6721a344'
test "$(git -C "$RUNNER_TEMP/k5d/Yggdrasil" hash-object research/native/itd02/r5/concurrent_cues.py)" = '4182889a47e31391a95ea3a2f5d8a4b87bcd6359'
export PYTHONPATH="$RUNNER_TEMP/k5d/Yggdrasil:$GITHUB_WORKSPACE/research/lcrm01"
python -B -m unittest discover -s "$RUNNER_TEMP/k5d/Yggdrasil/research/native/itd02/r6" -p 'test_composer.py' -v
echo "K5D_ORIGINAL_MODEL_AND_ENVIRONMENT_AUTHENTIC=PASS"
set +e
python -B research/lcrm01/k5d_causal_trial.py --output "$RUNNER_TEMP/k5d/process-a.json" > "$RUNNER_TEMP/k5d/process-a.log" 2>&1
a=$?
python -B research/lcrm01/k5d_causal_trial.py --output "$RUNNER_TEMP/k5d/process-b.json" > "$RUNNER_TEMP/k5d/process-b.log" 2>&1
b=$?
set -e
echo "K5D_PROCESS_A_EXIT=$a K5D_PROCESS_B_EXIT=$b"
cat "$RUNNER_TEMP/k5d/process-a.log" "$RUNNER_TEMP/k5d/process-b.log"
test "$a" -eq 0 && test "$b" -eq 0
python -B research/lcrm01/k5d_compare.py --first "$RUNNER_TEMP/k5d/process-a.json" --second "$RUNNER_TEMP/k5d/process-b.json" --output "$RUNNER_TEMP/k5d/comparison.json"
test -z "$(git -C "$RUNNER_TEMP/k5d/Yggdrasil" status --porcelain --untracked-files=no)"
echo "K5D_TRUE_SOURCE_AND_DEVELOPMENT_SCIENCE=PASS"
