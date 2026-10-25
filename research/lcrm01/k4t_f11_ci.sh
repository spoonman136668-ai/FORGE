#!/usr/bin/env bash
# F11: precommitted original Farama source, fresh public hard-state interventions.
set -euo pipefail
cd "$GITHUB_WORKSPACE"
test "$(git rev-parse '49b6ede9c5607ade0fbf8483fcf366b17aa31672^')" = 5eba1c8f103eb32c72b937b074259fc5cc7fc1b4
git merge-base --is-ancestor 49b6ede9c5607ade0fbf8483fcf366b17aa31672 HEAD
test "$(git hash-object research/lcrm01/k4t_f11_frozen_hard_public.json)" = f20252e0d03d961a5b3d752501ed9b734a0698c2
test "$(git hash-object research/lcrm01/k4t_f8_paired_actions.py)" = 31302c29f3dab743e85b94666683d604092bce2c
test "$(git hash-object research/lcrm01/k4t_f9_randomized_value.py)" = 2737b0c437b51208ca4df983062272a8f4eb768a
test "$(git hash-object research/lcrm01/k4t_f10_public_history.py)" = 5d0222981a6fdff55930caa0e568f3f372a426d4
test "$(git hash-object research/lcrm01/k4r_minigrid_source.py)" = a09f73d528192f41e1e9572d9b8476a66cdff644
echo K4T_F11_ORIGINAL_HISTORIC_AND_FROZEN_SOURCE=PASS
python -B - <<'PY'
import ast
from pathlib import Path
for name in ("k4t_f11_hard_public_memory.py","test_k4t_f11_sourceonly.py","k4t_f11_compare.py"):
    ast.parse((Path("research/lcrm01")/name).read_text())
print("K4T_F11_SOURCE_PYTHON_PARSE=PASS")
PY
export PYTHONPATH="$GITHUB_WORKSPACE/research/lcrm01"
python -m pip install 'pip==24.0' 'setuptools==69.5.1' 'wheel==0.43.0'
python -m pip install 'numpy==1.26.4' 'gymnasium==1.1.1' 'pygame-ce==2.5.3'
python -B -m unittest discover -s research/lcrm01 -p test_k4t_f11_sourceonly.py -v
mkdir -p "$RUNNER_TEMP/k4tf11/minigrid"
git init -q "$RUNNER_TEMP/k4tf11/minigrid"
git -C "$RUNNER_TEMP/k4tf11/minigrid" remote add origin https://github.com/Farama-Foundation/Minigrid.git
git -C "$RUNNER_TEMP/k4tf11/minigrid" fetch --no-tags --depth 1 origin 7f5853792ea7f04f75614661006d87fcf949f26d
git -C "$RUNNER_TEMP/k4tf11/minigrid" checkout --detach -q 7f5853792ea7f04f75614661006d87fcf949f26d
test "$(git -C "$RUNNER_TEMP/k4tf11/minigrid" hash-object minigrid/envs/empty.py)" = 8810bb0fa156d18475022edd8859b135ef745a5f
test "$(git -C "$RUNNER_TEMP/k4tf11/minigrid" hash-object minigrid/envs/fourrooms.py)" = d79f007e00f95f48284da66d760872483c02fab2
test "$(git -C "$RUNNER_TEMP/k4tf11/minigrid" hash-object minigrid/wrappers.py)" = 1eb2da8fb612653c97f443ff6c7492ed3f1aaa80
test "$(git -C "$RUNNER_TEMP/k4tf11/minigrid" hash-object minigrid/minigrid_env.py)" = eb29e9a902de0715ab77ec981a2113576d7664fa
python -m pip install --no-deps -e "$RUNNER_TEMP/k4tf11/minigrid"
echo K4T_F11_FARAMA_ORIGINAL_SOURCE_IMMUTABLE=PASS
python -B research/lcrm01/k4t_f11_hard_public_memory.py --output "$RUNNER_TEMP/k4tf11/process-a.json" > "$RUNNER_TEMP/k4tf11/process-a.log" 2>&1 || {
 cat "$RUNNER_TEMP/k4tf11/process-a.log"
 echo K4T_F11_PROCESS_A_STOP_BEFORE_SCIENTIFIC_CLAIM
 exit 1
}
python -B research/lcrm01/k4t_f11_hard_public_memory.py --output "$RUNNER_TEMP/k4tf11/process-b.json" > "$RUNNER_TEMP/k4tf11/process-b.log" 2>&1 || {
 cat "$RUNNER_TEMP/k4tf11/process-b.log"
 echo K4T_F11_PROCESS_B_STOP_BEFORE_SCIENTIFIC_CLAIM
 exit 1
}
cat "$RUNNER_TEMP/k4tf11/process-a.log"
cat "$RUNNER_TEMP/k4tf11/process-b.log"
python -B research/lcrm01/k4t_f11_compare.py \
 --first "$RUNNER_TEMP/k4tf11/process-a.json" \
 --second "$RUNNER_TEMP/k4tf11/process-b.json" \
 --output "$RUNNER_TEMP/k4tf11/comparison.json"
python -B - <<'PY'
import json,os
from pathlib import Path
root=Path(os.environ["RUNNER_TEMP"])/"k4tf11"
a=json.loads((root/"process-a.json").read_text())
b=json.loads((root/"process-b.json").read_text())
c=json.loads((root/"comparison.json").read_text())
assert c["science_identical"] is True
assert c["scientific_accepted"] is False
assert a["equal_FIT_action_exposures_for_all_models"]==3*len(a["true_FIT_paired_action_training"])
assert len(a["true_fresh_DEV_paired_action_evaluation"])>0
assert a["native_R5_source_unchanged"] is True
print("K4T_F11_TWO_INDEPENDENT_GENUINE_SOURCE_PROCESSES=PASS")
print("K4T_F11_FROZEN_OFFICIAL_RESULT="+c["result"])
PY
test -z "$(git status --porcelain --untracked-files=all)"
echo K4T_F11_ORIGINAL_REPOSITORY_CLEAN=PASS
echo K4T_F11_PROTECTED_FIRST_USE=NOT_PERFORMED
