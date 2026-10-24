#!/usr/bin/env bash
# Original K4P source-aware, FIT-first predictive state. No controller owner change.
set -euo pipefail
cd "$GITHUB_WORKSPACE"
test "$(git rev-parse '7b8896ad48a86a2279b6b3d88d49ed19dc6fbec4^')" = 'bb692c4897cc646858728c3cbc349d533b482b1d'
git merge-base --is-ancestor 7b8896ad48a86a2279b6b3d88d49ed19dc6fbec4 HEAD
test "$(git hash-object research/lcrm01/k4p_frozen_predictive_state.json)" = '09dc7e516e942e4728325fbe2c78b49b6185e7d7'
test "$(git hash-object research/lcrm01/k4o_frozen_mechanism_audit.json)" = '93b996c20d2c58547ba19b2576b395605dd785b3'
test "$(git hash-object research/lcrm01/k4n_frozen_decision_coreset.json)" = '6c5265daf4dcf3db11fda4051f20f8ec780b9b54'
echo 'a6e97b95fcfa3fc74e9b9fa28ffc22640d99c8fc0f4da31a10336c0f6906e270  research/lcrm01/k4a_control_replay.py' | sha256sum -c -
echo '1a6169bba4f77bb28519766184636c89bfcdc5b5ab23485475e64de474ea09bb  research/lcrm01/k4b_replay_state_repair.py' | sha256sum -c -
python -m pip install 'pip==24.0' 'setuptools==69.5.1' 'wheel==0.43.0'
mkdir -p "$RUNNER_TEMP/k4p/wheels"
python -m pip download --only-binary=:all: --no-deps --dest "$RUNNER_TEMP/k4p/wheels" 'pybullet==3.2.5'
file=$(find "$RUNNER_TEMP/k4p/wheels" -maxdepth 1 -name 'pybullet-3.2.5-cp39-cp39-manylinux*.whl' -print -quit)
test -n "$file"
printf '9adcaa00de674a02549949f6f8d51b485bd7a23fbc87a1defb2067e1364f8202  %s\n' "$file" | sha256sum -c -
python -m pip install --no-deps "$file"
python -m pip install 'numpy==1.23.5' 'scipy==1.10.1' 'gym==0.17.2' 'catkin_pkg==0.5.2' 'matplotlib==3.7.5' 'psutil==5.9.8'
PYTHONPATH="$GITHUB_WORKSPACE/research/lcrm01" python -B -m unittest discover -s research/lcrm01 -p 'test_k4p_sourceonly.py' -v
git init -q "$RUNNER_TEMP/k4p/CausalWorld"
git -C "$RUNNER_TEMP/k4p/CausalWorld" remote add origin https://github.com/rr-learning/CausalWorld.git
git -C "$RUNNER_TEMP/k4p/CausalWorld" fetch --no-tags --depth 1 origin 1045277101a92c506db42704da28f6e7227d401b
git -C "$RUNNER_TEMP/k4p/CausalWorld" checkout --detach -q 1045277101a92c506db42704da28f6e7227d401b
test "$(git -C "$RUNNER_TEMP/k4p/CausalWorld" hash-object causal_world/envs/causalworld.py)" = '6169fcd629e5721e889fbcada52c06e9c2a37b0e'
export PYTHONPATH="$GITHUB_WORKSPACE/research/lcrm01/k4a_overlay:$GITHUB_WORKSPACE/research/lcrm01"
set +e
python -B research/lcrm01/k4p_predictive_state.py --causalworld-repo "$RUNNER_TEMP/k4p/CausalWorld" --output "$RUNNER_TEMP/k4p/process-a.json" > "$RUNNER_TEMP/k4p/process-a.log" 2>&1
a=$?
python -B research/lcrm01/k4p_predictive_state.py --causalworld-repo "$RUNNER_TEMP/k4p/CausalWorld" --output "$RUNNER_TEMP/k4p/process-b.json" > "$RUNNER_TEMP/k4p/process-b.log" 2>&1
b=$?
set -e
echo "K4P_PROCESS_A_EXIT=$a K4P_PROCESS_B_EXIT=$b"
cat "$RUNNER_TEMP/k4p/process-a.log" "$RUNNER_TEMP/k4p/process-b.log"
test "$a" -eq 0 && test "$b" -eq 0
python -B research/lcrm01/k4p_compare.py --first "$RUNNER_TEMP/k4p/process-a.json" --second "$RUNNER_TEMP/k4p/process-b.json" --output "$RUNNER_TEMP/k4p/comparison.json"
test -z "$(git -C "$RUNNER_TEMP/k4p/CausalWorld" status --porcelain --untracked-files=no)"
python -B - <<'PY'
import json,os
from pathlib import Path
root=Path(os.environ["RUNNER_TEMP"])/"k4p"
a=json.loads((root/"process-a.json").read_text())
b=json.loads((root/"process-b.json").read_text())
c=json.loads((root/"comparison.json").read_text())
assert a["schema"]==b["schema"]=="mass.lcrm01.k4p.original-public-predictive-state-study.v1"
assert a["FIT_episodes"]==b["FIT_episodes"]==96
assert (a["CHECK_episodes"],a["DEV_episodes"]) in ((0,0),(24,96))
assert a["original_K4N_no_go_preserved"] and b["original_K4N_no_go_preserved"]
assert a["original_K4O_diagnostic_preserved"] and b["original_K4O_diagnostic_preserved"]
assert not a["scientific_first_use"] and not b["scientific_first_use"]
assert not a["scientific_accepted"] and not b["scientific_accepted"]
assert c["exact_original_science_agreement"] is True
print("K4P_ORIGINAL_RESEARCH_VERDICT="+c["result"])
PY
