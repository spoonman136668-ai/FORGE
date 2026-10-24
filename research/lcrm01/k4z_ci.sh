#!/usr/bin/env bash
set -euo pipefail
cd "$GITHUB_WORKSPACE"
test "$(git rev-parse '721afd33189f5fcba50ded37d8d4bdf01c3572e0^')" = 'b01627841e6014750b3f03bcd58873d08375f93d'
git merge-base --is-ancestor 721afd33189f5fcba50ded37d8d4bdf01c3572e0 HEAD
test "$(git hash-object research/lcrm01/k4z_frozen_episodic_nav.json)" = 'ccfcbadc55570a13701cee8175290700e9f14865'
test "$(git hash-object research/lcrm01/k4y_frozen_learned_affordance.json)" = 'c34ac2b73e07c0117ff0bea863addd358749e9cb'
echo "K4Z_FROZEN_FIRST_USE_PREREG=PASS"
python -B - <<'PY'
import ast,pathlib
for name in ("k4z_episodic_navigation.py","k4z_compare.py"):
 ast.parse((pathlib.Path("research/lcrm01")/name).read_text())
print("K4Z_AST_SOURCE_GATE=PASS")
PY
export PYTHONPATH="$GITHUB_WORKSPACE/research/lcrm01"
python -B -m unittest discover -s research/lcrm01 -p 'test_k4z_sourceonly.py' -v
mkdir -p "$RUNNER_TEMP/k4z"
python -m pip install 'pip==24.0' 'setuptools==69.5.1' 'wheel==0.43.0'
python -m pip install 'numpy==1.26.4' 'gymnasium==1.1.1' 'pygame-ce==2.5.3'
git init -q "$RUNNER_TEMP/k4z/minigrid"
git -C "$RUNNER_TEMP/k4z/minigrid" remote add origin https://github.com/Farama-Foundation/Minigrid.git
git -C "$RUNNER_TEMP/k4z/minigrid" fetch --no-tags --depth 1 origin 7f5853792ea7f04f75614661006d87fcf949f26d
git -C "$RUNNER_TEMP/k4z/minigrid" checkout --detach -q 7f5853792ea7f04f75614661006d87fcf949f26d
test "$(git -C "$RUNNER_TEMP/k4z/minigrid" hash-object minigrid/envs/empty.py)" = '8810bb0fa156d18475022edd8859b135ef745a5f'
test "$(git -C "$RUNNER_TEMP/k4z/minigrid" hash-object minigrid/envs/fourrooms.py)" = 'd79f007e00f95f48284da66d760872483c02fab2'
test "$(git -C "$RUNNER_TEMP/k4z/minigrid" hash-object minigrid/wrappers.py)" = '1eb2da8fb612653c97f443ff6c7492ed3f1aaa80'
test "$(git -C "$RUNNER_TEMP/k4z/minigrid" hash-object minigrid/minigrid_env.py)" = 'eb29e9a902de0715ab77ec981a2113576d7664fa'
python -m pip install --no-deps -e "$RUNNER_TEMP/k4z/minigrid"
git init -q "$RUNNER_TEMP/k4z/Yggdrasil"
git -C "$RUNNER_TEMP/k4z/Yggdrasil" remote add origin https://github.com/spoonman136668-ai/Yggdrasil.git
git -C "$RUNNER_TEMP/k4z/Yggdrasil" fetch --no-tags --depth 1 origin fbf78bcc6988755ba0e3e026f06d273839c1fa9f
git -C "$RUNNER_TEMP/k4z/Yggdrasil" checkout --detach -q fbf78bcc6988755ba0e3e026f06d273839c1fa9f
test "$(git -C "$RUNNER_TEMP/k4z/Yggdrasil" hash-object research/native/itd02/r2/affordance_cells.py)" = 'f7e47dfef309e1c0bcc871d518154fd950b3eca0'
test "$(git -C "$RUNNER_TEMP/k4z/Yggdrasil" hash-object research/native/itd02/r3/navigator.py)" = '5348238f4ec2183bea29262659883391b5f429fd'
test "$(git -C "$RUNNER_TEMP/k4z/Yggdrasil" hash-object research/native/itd02/r3/PREREG.json)" = 'd518e5443d0d6462f8fa32fb41283c8a26aca2ad'
export PYTHONPATH="$RUNNER_TEMP/k4z/Yggdrasil:$GITHUB_WORKSPACE/research/lcrm01"
python -B -m unittest discover -s "$RUNNER_TEMP/k4z/Yggdrasil/research/native/itd02/r3" -p 'test_navigator.py' -v
echo "K4Z_ALL_ORIGINAL_SOURCES_AUTHENTIC=PASS"
# Two process reports use the exact same preregistered new source worlds and
# are generated only AFTER all local/source first-use proof checks passed.
set +e
python -B research/lcrm01/k4z_episodic_navigation.py --output "$RUNNER_TEMP/k4z/process-a.json" \
  > "$RUNNER_TEMP/k4z/process-a.log" 2>&1
a=$?
python -B research/lcrm01/k4z_episodic_navigation.py --output "$RUNNER_TEMP/k4z/process-b.json" \
  > "$RUNNER_TEMP/k4z/process-b.log" 2>&1
b=$?
set -e
echo "K4Z_PROCESS_A_EXIT=$a K4Z_PROCESS_B_EXIT=$b"
cat "$RUNNER_TEMP/k4z/process-a.log" "$RUNNER_TEMP/k4z/process-b.log"
test "$a" -eq 0 && test "$b" -eq 0
python -B research/lcrm01/k4z_compare.py \
 --first "$RUNNER_TEMP/k4z/process-a.json" \
 --second "$RUNNER_TEMP/k4z/process-b.json" \
 --output "$RUNNER_TEMP/k4z/comparison.json"
test -z "$(git -C "$RUNNER_TEMP/k4z/minigrid" status --porcelain --untracked-files=no)"
test -z "$(git -C "$RUNNER_TEMP/k4z/Yggdrasil" status --porcelain --untracked-files=no)"
python -B - <<'PY'
import json,os,pathlib
root=pathlib.Path(os.environ["RUNNER_TEMP"])/"k4z"
a=json.loads((root/"process-a.json").read_text())
b=json.loads((root/"process-b.json").read_text())
c=json.loads((root/"comparison.json").read_text())
assert a["FIT_original_experience_count"]==b["FIT_original_experience_count"]==12000
assert a["DEV_real_episodes"]==b["DEV_real_episodes"]==112
assert c["exact_original_source_science_agreement"] is True
assert c["scientific_accepted"] is False
print("K4Z_REAL_FIRSTUSE_NEGATIVE_CUSTODY_PASS")
print("K4Z_SOURCE_CONCLUSION="+c["result"])
PY
