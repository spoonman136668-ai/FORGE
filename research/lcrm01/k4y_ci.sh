#!/usr/bin/env bash
# K4Y authentic original MiniGrid / native R1/R2, independent controller-free.
set -euo pipefail
cd "$GITHUB_WORKSPACE"
test "$(git rev-parse 'e4df169f09adf613fbb614af98adbfb251d6c09d^')" = '2e3ff3d173f250be1324b2a79cc484bbcbf68a97'
git merge-base --is-ancestor e4df169f09adf613fbb614af98adbfb251d6c09d HEAD
test "$(git hash-object research/lcrm01/k4y_frozen_learned_affordance.json)" = 'c34ac2b73e07c0117ff0bea863addd358749e9cb'
test "$(git hash-object research/lcrm01/k4x_frozen_curriculum_intervention.json)" = '664f0c92070ed5bedc70ba934edce9adaf9cdb4f'
echo 'K4Y_FROZEN_NEW_SOURCE_BEFORE_FIRST_USE=PASS'
python -B - <<'PY'
import ast,pathlib
for x in ("k4y_native_affordance.py","k4y_compare.py","k4y_fetch_sources.py"):
 ast.parse((pathlib.Path("research/lcrm01")/x).read_text())
print("K4Y_SOURCE_AST=PASS")
PY
export PYTHONPATH="$GITHUB_WORKSPACE/research/lcrm01"
python -B -m unittest discover -s research/lcrm01 -p 'test_k4y_sourceonly.py' -v
mkdir -p "$RUNNER_TEMP/k4y/minigrid" "$RUNNER_TEMP/k4y/go/research/native/itd02/r1" "$RUNNER_TEMP/k4y/go/research/native/itd02/r2" "$RUNNER_TEMP/k4y/yggroot/research/native/itd02/r1" "$RUNNER_TEMP/k4y/yggroot/research/native/itd02/r2"
python -m pip install 'pip==24.0' 'setuptools==69.5.1' 'wheel==0.43.0'
python -m pip install 'numpy==1.26.4' 'gymnasium==1.1.1' 'pygame-ce==2.5.3'
git init -q "$RUNNER_TEMP/k4y/minigrid"
git -C "$RUNNER_TEMP/k4y/minigrid" remote add origin https://github.com/Farama-Foundation/Minigrid.git
git -C "$RUNNER_TEMP/k4y/minigrid" fetch --no-tags --depth 1 origin 7f5853792ea7f04f75614661006d87fcf949f26d
git -C "$RUNNER_TEMP/k4y/minigrid" checkout --detach -q 7f5853792ea7f04f75614661006d87fcf949f26d
test "$(git -C "$RUNNER_TEMP/k4y/minigrid" hash-object minigrid/envs/empty.py)" = '8810bb0fa156d18475022edd8859b135ef745a5f'
test "$(git -C "$RUNNER_TEMP/k4y/minigrid" hash-object minigrid/envs/fourrooms.py)" = 'd79f007e00f95f48284da66d760872483c02fab2'
test "$(git -C "$RUNNER_TEMP/k4y/minigrid" hash-object minigrid/wrappers.py)" = '1eb2da8fb612653c97f443ff6c7492ed3f1aaa80'
test "$(git -C "$RUNNER_TEMP/k4y/minigrid" hash-object minigrid/minigrid_env.py)" = 'eb29e9a902de0715ab77ec981a2113576d7664fa'
python -m pip install --no-deps -e "$RUNNER_TEMP/k4y/minigrid"
python -B research/lcrm01/k4y_fetch_sources.py \
 --wingless-R1 "$RUNNER_TEMP/k4y/go/research/native/itd02/r1/policy.go" \
 --wingless-R2 "$RUNNER_TEMP/k4y/go/research/native/itd02/r2/affordance.go" \
 --yggdrasil-R1 "$RUNNER_TEMP/k4y/yggroot/research/native/itd02/r1/native_policy.py" \
 --yggdrasil-R2 "$RUNNER_TEMP/k4y/yggroot/research/native/itd02/r2/affordance_cells.py"
cp "$RUNNER_TEMP/k4y/yggroot/research/native/itd02/r1/native_policy.py" "$RUNNER_TEMP/k4y/yggroot/native_policy.py"
printf 'module github.com/spoonman136668-ai/Wingless\n\ngo 1.25.0\n' > "$RUNNER_TEMP/k4y/go/go.mod"
sed 's|"k4u/wingless"|"github.com/spoonman136668-ai/Wingless/research/native/itd02/r1"|' research/lcrm01/k4u_wingless_bridge.go > "$RUNNER_TEMP/k4y/go/bridge_r1.go"
cp research/lcrm01/k4y_wingless_r2_bridge.go "$RUNNER_TEMP/k4y/go/bridge_r2.go"
(cd "$RUNNER_TEMP/k4y/go" && go build -trimpath -o "$RUNNER_TEMP/k4y/wingless-r1" bridge_r1.go)
(cd "$RUNNER_TEMP/k4y/go" && go build -trimpath -o "$RUNNER_TEMP/k4y/wingless-r2" bridge_r2.go)
export PYTHONPATH="$RUNNER_TEMP/k4y/yggroot:$GITHUB_WORKSPACE/research/lcrm01"
set +e
python -B research/lcrm01/k4y_native_affordance.py \
 --wingless-r1 "$RUNNER_TEMP/k4y/wingless-r1" \
 --wingless-r2 "$RUNNER_TEMP/k4y/wingless-r2" \
 --yggdrasil-source "$RUNNER_TEMP/k4y/yggroot" \
 --output "$RUNNER_TEMP/k4y/process-a.json" > "$RUNNER_TEMP/k4y/process-a.log" 2>&1
a=$?
python -B research/lcrm01/k4y_native_affordance.py \
 --wingless-r1 "$RUNNER_TEMP/k4y/wingless-r1" \
 --wingless-r2 "$RUNNER_TEMP/k4y/wingless-r2" \
 --yggdrasil-source "$RUNNER_TEMP/k4y/yggroot" \
 --output "$RUNNER_TEMP/k4y/process-b.json" > "$RUNNER_TEMP/k4y/process-b.log" 2>&1
b=$?
set -e
echo "K4Y_PROCESS_A_EXIT=$a K4Y_PROCESS_B_EXIT=$b"
cat "$RUNNER_TEMP/k4y/process-a.log" "$RUNNER_TEMP/k4y/process-b.log"
test "$a" -eq 0 && test "$b" -eq 0
python -B research/lcrm01/k4y_compare.py \
 --first "$RUNNER_TEMP/k4y/process-a.json" \
 --second "$RUNNER_TEMP/k4y/process-b.json" \
 --output "$RUNNER_TEMP/k4y/comparison.json"
test -z "$(git -C "$RUNNER_TEMP/k4y/minigrid" status --porcelain --untracked-files=no)"
python -B - <<'PY'
import json,os,pathlib
root=pathlib.Path(os.environ["RUNNER_TEMP"])/"k4y"
a=json.loads((root/"process-a.json").read_text())
b=json.loads((root/"process-b.json").read_text())
c=json.loads((root/"comparison.json").read_text())
assert a["FIT_public_experience_count"]==b["FIT_public_experience_count"]==12000
assert a["CHECK_episodes"]==b["CHECK_episodes"]==72
assert a["DEV_episodes"]==b["DEV_episodes"]==144
assert a["scientific_accepted"] is False and b["scientific_accepted"] is False
assert c["exact_original_science_agreement"] is True
print("K4Y_SOURCE_AND_SCIENCE_REPEATED=PASS")
print("K4Y_NATIVE_AFFORDANCE_DISPOSITION="+c["result"])
PY
