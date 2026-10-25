#!/usr/bin/env bash
# F8 independently authored original-world, fully executed three-action trials
set -euo pipefail
cd "$GITHUB_WORKSPACE"
test "$(git rev-parse 'cd96f96af5b5bbfbfd74a2c07ae98fe81d0c4be2^')" = 1ca269d19f81c295f196068c5d354dd5991c1a8e
git merge-base --is-ancestor cd96f96af5b5bbfbfd74a2c07ae98fe81d0c4be2 HEAD
test "$(git hash-object research/lcrm01/k4t_f9_frozen_randomized_value.json)" = 35ad5e1ac6b227e03abd2965ddc5d7c9e837a3a3
test "$(git hash-object research/lcrm01/k4t_f8_paired_actions.py)" = 31302c29f3dab743e85b94666683d604092bce2c
test "$(git hash-object research/lcrm01/k4x_curriculum_intervention.py)" = e9cac7e9b47a9e19483b6b05d0afd0ecbaf4ab59
test "$(git hash-object research/lcrm01/k4r_minigrid_source.py)" = a09f73d528192f41e1e9572d9b8476a66cdff644
echo K4T_F9_FROZEN_PROSPECTIVE_BEFORE_ORIGINAL_SOURCE=PASS
python -B - <<'PY'
import ast,pathlib
for name in ("k4t_f9_randomized_value.py","k4t_f9_compare.py","test_k4t_f9_sourceonly.py"):
 ast.parse((pathlib.Path("research/lcrm01")/name).read_text())
print("K4T_F9_AST_PASS")
PY
export PYTHONPATH="$GITHUB_WORKSPACE/research/lcrm01"
# Run the numpy-backed fitted-model tests after pinning numerical dependencies.
python -m pip install 'pip==24.0' 'setuptools==69.5.1' 'wheel==0.43.0'
python -m pip install 'numpy==1.26.4' 'gymnasium==1.1.1' 'pygame-ce==2.5.3'
python -B -m unittest discover -s research/lcrm01 -p test_k4t_f9_sourceonly.py -v
mkdir -p "$RUNNER_TEMP/k4tf9/minigrid" "$RUNNER_TEMP/k4tf9"
git init -q "$RUNNER_TEMP/k4tf9/minigrid"
git -C "$RUNNER_TEMP/k4tf9/minigrid" remote add origin https://github.com/Farama-Foundation/Minigrid.git
git -C "$RUNNER_TEMP/k4tf9/minigrid" fetch --no-tags --depth 1 origin 7f5853792ea7f04f75614661006d87fcf949f26d
git -C "$RUNNER_TEMP/k4tf9/minigrid" checkout --detach -q 7f5853792ea7f04f75614661006d87fcf949f26d
test "$(git -C "$RUNNER_TEMP/k4tf9/minigrid" hash-object minigrid/envs/empty.py)" = 8810bb0fa156d18475022edd8859b135ef745a5f
test "$(git -C "$RUNNER_TEMP/k4tf9/minigrid" hash-object minigrid/envs/fourrooms.py)" = d79f007e00f95f48284da66d760872483c02fab2
test "$(git -C "$RUNNER_TEMP/k4tf9/minigrid" hash-object minigrid/wrappers.py)" = 1eb2da8fb612653c97f443ff6c7492ed3f1aaa80
test "$(git -C "$RUNNER_TEMP/k4tf9/minigrid" hash-object minigrid/minigrid_env.py)" = eb29e9a902de0715ab77ec981a2113576d7664fa
python -m pip install --no-deps -e "$RUNNER_TEMP/k4tf9/minigrid"
echo K4T_F9_ORIGINAL_IMMUTABLE_MINIGRID_SOURCE=PASS
python -B research/lcrm01/k4t_f9_randomized_value.py --output "$RUNNER_TEMP/k4tf9/process-a.json" > "$RUNNER_TEMP/k4tf9/process-a.log" 2>&1 || {
 cat "$RUNNER_TEMP/k4tf9/process-a.log"
 echo K4T_F9_PROCESS_A_INFRASTRUCTURE_BLOCKED
 exit 1
}
python -B research/lcrm01/k4t_f9_randomized_value.py --output "$RUNNER_TEMP/k4tf9/process-b.json" > "$RUNNER_TEMP/k4tf9/process-b.log" 2>&1 || {
 cat "$RUNNER_TEMP/k4tf9/process-b.log"
 echo K4T_F9_PROCESS_B_INFRASTRUCTURE_BLOCKED
 exit 1
}
cat "$RUNNER_TEMP/k4tf9/process-a.log"
cat "$RUNNER_TEMP/k4tf9/process-b.log"
python -B research/lcrm01/k4t_f9_compare.py \
 --first "$RUNNER_TEMP/k4tf9/process-a.json" \
 --second "$RUNNER_TEMP/k4tf9/process-b.json" \
 --output "$RUNNER_TEMP/k4tf9/comparison.json"
python -B - <<'PY'
import json,os
from pathlib import Path
root=Path(os.environ["RUNNER_TEMP"])/"k4tf9"
a=json.loads((root/"process-a.json").read_text())
b=json.loads((root/"process-b.json").read_text())
c=json.loads((root/"comparison.json").read_text())
assert c["science_identical"] is True
assert c["scientific_first_use"] is False
assert len(a["original_source_training"])==len(b["original_source_training"])>0
assert len(a["original_source_prospective_evaluation"])==len(b["original_source_prospective_evaluation"])>0
assert a["FIT_trained_action_return_count"]==3*len(a["original_source_training"])
assert set(a["summary"])=={"empty","fourrooms"}
print("K4T_F9_TWO_INDEPENDENT_ORIGINAL_SOURCE_PAIRED_PROCESSES=PASS")
print("K4T_F9_OFFICIAL_DISPOSITION="+c["result"])
PY
test -z "$(git status --porcelain --untracked-files=all)"
echo K4T_F9_CLEAN_DEVELOPMENT_SOURCE=PASS
echo K4T_F9_PROTECTED_SCIENTIFIC_FIRST_USE=FALSE
