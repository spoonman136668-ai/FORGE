#!/usr/bin/env bash
# F10 precommitted original-world historical information sufficiency.
set -euo pipefail
cd "$GITHUB_WORKSPACE"
test "$(git rev-parse '80fd129248299f137396e3c8f0a1540b9ec2b012^')" = 04ba6098b609c9417b982267cedd826a1ecd6349
git merge-base --is-ancestor 80fd129248299f137396e3c8f0a1540b9ec2b012 HEAD
test "$(git hash-object research/lcrm01/k4t_f10_frozen_history.json)" = 05370b077ab9148ae30beb91faf9a5126c92309e
test "$(git hash-object research/lcrm01/k4t_f8_paired_actions.py)" = 31302c29f3dab743e85b94666683d604092bce2c
test "$(git hash-object research/lcrm01/k4t_f9_randomized_value.py)" = 2737b0c437b51208ca4df983062272a8f4eb768a
test "$(git hash-object research/lcrm01/k4r_minigrid_source.py)" = a09f73d528192f41e1e9572d9b8476a66cdff644
echo K4T_F10_ORIGINAL_SOURCE_AND_FROZEN_HYPOTHESIS=PASS
python -B - <<'PY'
import ast,pathlib
for name in ("k4t_f10_public_history.py","k4t_f10_compare.py","test_k4t_f10_sourceonly.py"):
 ast.parse((pathlib.Path("research/lcrm01")/name).read_text())
print("K4T_F10_SOURCE_PYTHON_AST=PASS")
PY
export PYTHONPATH="$GITHUB_WORKSPACE/research/lcrm01"
python -m pip install 'pip==24.0' 'setuptools==69.5.1' 'wheel==0.43.0'
python -m pip install 'numpy==1.26.4' 'gymnasium==1.1.1' 'pygame-ce==2.5.3'
python -B -m unittest discover -s research/lcrm01 -p test_k4t_f10_sourceonly.py -v
mkdir -p "$RUNNER_TEMP/k4tf10/minigrid"
git init -q "$RUNNER_TEMP/k4tf10/minigrid"
git -C "$RUNNER_TEMP/k4tf10/minigrid" remote add origin https://github.com/Farama-Foundation/Minigrid.git
git -C "$RUNNER_TEMP/k4tf10/minigrid" fetch --no-tags --depth 1 origin 7f5853792ea7f04f75614661006d87fcf949f26d
git -C "$RUNNER_TEMP/k4tf10/minigrid" checkout --detach -q 7f5853792ea7f04f75614661006d87fcf949f26d
test "$(git -C "$RUNNER_TEMP/k4tf10/minigrid" hash-object minigrid/envs/empty.py)" = 8810bb0fa156d18475022edd8859b135ef745a5f
test "$(git -C "$RUNNER_TEMP/k4tf10/minigrid" hash-object minigrid/envs/fourrooms.py)" = d79f007e00f95f48284da66d760872483c02fab2
test "$(git -C "$RUNNER_TEMP/k4tf10/minigrid" hash-object minigrid/wrappers.py)" = 1eb2da8fb612653c97f443ff6c7492ed3f1aaa80
test "$(git -C "$RUNNER_TEMP/k4tf10/minigrid" hash-object minigrid/minigrid_env.py)" = eb29e9a902de0715ab77ec981a2113576d7664fa
python -m pip install --no-deps -e "$RUNNER_TEMP/k4tf10/minigrid"
echo K4T_F10_GENUINE_IMMUTABLE_ORIGINAL_MINIGRID=PASS
python -B research/lcrm01/k4t_f10_public_history.py --output "$RUNNER_TEMP/k4tf10/process-a.json" > "$RUNNER_TEMP/k4tf10/process-a.log" 2>&1 || {
 cat "$RUNNER_TEMP/k4tf10/process-a.log"
 echo K4T_F10_PROCESS_A_BLOCKED_BEFORE_SCIENCE
 exit 1
}
python -B research/lcrm01/k4t_f10_public_history.py --output "$RUNNER_TEMP/k4tf10/process-b.json" > "$RUNNER_TEMP/k4tf10/process-b.log" 2>&1 || {
 cat "$RUNNER_TEMP/k4tf10/process-b.log"
 echo K4T_F10_PROCESS_B_BLOCKED_BEFORE_SCIENCE
 exit 1
}
cat "$RUNNER_TEMP/k4tf10/process-a.log"
cat "$RUNNER_TEMP/k4tf10/process-b.log"
python -B research/lcrm01/k4t_f10_compare.py \
 --first "$RUNNER_TEMP/k4tf10/process-a.json" \
 --second "$RUNNER_TEMP/k4tf10/process-b.json" \
 --output "$RUNNER_TEMP/k4tf10/comparison.json"
python -B - <<'PY'
import json,os
from pathlib import Path
root=Path(os.environ["RUNNER_TEMP"])/"k4tf10"
a=json.loads((root/"process-a.json").read_text())
b=json.loads((root/"process-b.json").read_text())
c=json.loads((root/"comparison.json").read_text())
assert c["science_identical"] is True
assert c["scientific_accepted"] is False
assert a["all_models_same_true_three_arm_source_FIT_count"]==3*len(a["true_randomized_FIT_episodes"])
assert len(a["true_randomized_fresh_DEV_episodes"])>0
assert a["native_R5_untouched"] is True
print("K4T_F10_TWO_INDEPENDENT_SOURCE_PROCESSES_AND_HISTORIES=PASS")
print("K4T_F10_OFFICIAL_PRECOMMITTED_DISPOSITION="+c["result"])
PY
test -z "$(git status --porcelain --untracked-files=all)"
echo K4T_F10_GIT_CLEAN_SOURCE_ONLY=PASS
echo K4T_F10_PROTECTED_SCIENTIFIC_FIRST_USE=FALSE
