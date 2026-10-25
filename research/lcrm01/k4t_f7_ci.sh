#!/usr/bin/env bash
# F7 source-only prospective training FIT delayed reward predictability.
set -euo pipefail
cd "$GITHUB_WORKSPACE"
test "$(git rev-parse '3753dca6b2d99f3fa133fa9aaf84354be12d8d59^')" = ccbd06822c17c585a34069e44b3ea736c9008872
git merge-base --is-ancestor 3753dca6b2d99f3fa133fa9aaf84354be12d8d59 HEAD
test "$(git hash-object research/lcrm01/k4t_f7_frozen_delayed_value.json)" = 1432770f414e07b9254e135cf09f597c39eefa49
test "$(git hash-object research/lcrm01/k4x_curriculum_intervention.py)" = e9cac7e9b47a9e19483b6b05d0afd0ecbaf4ab59
test "$(git hash-object research/lcrm01/k4y_native_affordance.py)" = 251ca00f7334809ef9afe815992272d0e3a68379
test "$(git hash-object research/lcrm01/k4r_minigrid_source.py)" = a09f73d528192f41e1e9572d9b8476a66cdff644
echo K4T_F7_FROZEN_BEFORE_NEW_SOURCE=PASS
python -B - <<'PY'
import ast,pathlib
for name in ("k4t_f7_delayed_value.py","k4t_f7_compare.py","test_k4t_f7_sourceonly.py"):
 ast.parse((pathlib.Path("research/lcrm01")/name).read_text())
print("K4T_F7_PYTHON_PARSE=PASS")
PY
export PYTHONPATH="$GITHUB_WORKSPACE/research/lcrm01"
python -B -m unittest discover -s research/lcrm01 -p test_k4t_f7_sourceonly.py -v
python -m pip install 'pip==24.0' 'setuptools==69.5.1' 'wheel==0.43.0'
python -m pip install 'numpy==1.26.4' 'gymnasium==1.1.1' 'pygame-ce==2.5.3'
mkdir -p "$RUNNER_TEMP/k4tf7/minigrid" "$RUNNER_TEMP/k4tf7"
git init -q "$RUNNER_TEMP/k4tf7/minigrid"
git -C "$RUNNER_TEMP/k4tf7/minigrid" remote add origin https://github.com/Farama-Foundation/Minigrid.git
git -C "$RUNNER_TEMP/k4tf7/minigrid" fetch --no-tags --depth 1 origin 7f5853792ea7f04f75614661006d87fcf949f26d
git -C "$RUNNER_TEMP/k4tf7/minigrid" checkout --detach -q 7f5853792ea7f04f75614661006d87fcf949f26d
test "$(git -C "$RUNNER_TEMP/k4tf7/minigrid" hash-object minigrid/envs/empty.py)" = 8810bb0fa156d18475022edd8859b135ef745a5f
test "$(git -C "$RUNNER_TEMP/k4tf7/minigrid" hash-object minigrid/envs/fourrooms.py)" = d79f007e00f95f48284da66d760872483c02fab2
test "$(git -C "$RUNNER_TEMP/k4tf7/minigrid" hash-object minigrid/wrappers.py)" = 1eb2da8fb612653c97f443ff6c7492ed3f1aaa80
test "$(git -C "$RUNNER_TEMP/k4tf7/minigrid" hash-object minigrid/minigrid_env.py)" = eb29e9a902de0715ab77ec981a2113576d7664fa
echo K4T_F7_ORIGINAL_MINIGRID_SOURCE=PASS
python -m pip install --no-deps -e "$RUNNER_TEMP/k4tf7/minigrid"
python -B research/lcrm01/k4t_f7_delayed_value.py --output "$RUNNER_TEMP/k4tf7/process-a.json" > "$RUNNER_TEMP/k4tf7/process-a.log" 2>&1 || {
 cat "$RUNNER_TEMP/k4tf7/process-a.log";echo K4T_F7_PROCESS_A_BLOCKED;exit 1;
}
python -B research/lcrm01/k4t_f7_delayed_value.py --output "$RUNNER_TEMP/k4tf7/process-b.json" > "$RUNNER_TEMP/k4tf7/process-b.log" 2>&1 || {
 cat "$RUNNER_TEMP/k4tf7/process-b.log";echo K4T_F7_PROCESS_B_BLOCKED;exit 1;
}
cat "$RUNNER_TEMP/k4tf7/process-a.log"
cat "$RUNNER_TEMP/k4tf7/process-b.log"
python -B research/lcrm01/k4t_f7_compare.py \
 --first "$RUNNER_TEMP/k4tf7/process-a.json" \
 --second "$RUNNER_TEMP/k4tf7/process-b.json" \
 --output "$RUNNER_TEMP/k4tf7/comparison.json"
python -B - <<'PY'
import json,os
from pathlib import Path
root=Path(os.environ["RUNNER_TEMP"])/"k4tf7"
a=json.loads((root/"process-a.json").read_text())
b=json.loads((root/"process-b.json").read_text())
c=json.loads((root/"comparison.json").read_text())
assert len(a["original_public_FIT_selected_action_events"])==len(b["original_public_FIT_selected_action_events"])==12000
assert c["science_identical"] is True
assert c["scientific_accepted"] is False and c["no_causal_unchosen_action_claim"] is True
assert a["observed_logged_selected_action_value_only"] and a["not_new_R5_navigation_policy"]
print("K4T_F7_TRUE_SOURCE_TWO_PROCESS_SCIENCE_CUSTODY=PASS")
print("K4T_F7_TRAIN_ONLY_DISPOSITION="+c["result"])
PY
test -z "$(git status --porcelain --untracked-files=all)"
echo K4T_F7_CLEAN_RESEARCH_ONLY=PASS
echo K4T_F7_PROTECTED_WORLD_FIRST_USE=NOT_PERFORMED
