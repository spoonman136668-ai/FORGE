#!/usr/bin/env bash
set -euo pipefail
cd "$GITHUB_WORKSPACE"
test "$(git rev-parse '602b16c0d157962580c4658f06c4b41eb064116a^')" = 'ccd593e342f17d742fa4fe8f3cab93bfe113c8f4'
git merge-base --is-ancestor 602b16c0d157962580c4658f06c4b41eb064116a HEAD
test "$(git hash-object research/lcrm01/k4n_frozen_decision_coreset.json)" = '6c5265daf4dcf3db11fda4051f20f8ec780b9b54'
test "$(git hash-object research/lcrm01/k4m_frozen_mechanism_audit.json)" = '05c20db23e563e028bb4f7f7b22fd00a05f0b32f'
test "$(git hash-object research/lcrm01/k4l_frozen_multicontext.json)" = 'c69aec62a50417947f3ad6e9615a2afc55625033'
echo 'a6e97b95fcfa3fc74e9b9fa28ffc22640d99c8fc0f4da31a10336c0f6906e270  research/lcrm01/k4a_control_replay.py' | sha256sum -c -
python -m pip install 'pip==24.0' 'setuptools==69.5.1' 'wheel==0.43.0'
mkdir -p "$RUNNER_TEMP/k4n/wheels"
python -m pip download --only-binary=:all: --no-deps --dest "$RUNNER_TEMP/k4n/wheels" 'pybullet==3.2.5'
file=$(find "$RUNNER_TEMP/k4n/wheels" -maxdepth 1 -name 'pybullet-3.2.5-cp39-cp39-manylinux*.whl' -print -quit)
test -n "$file"
printf '9adcaa00de674a02549949f6f8d51b485bd7a23fbc87a1defb2067e1364f8202  %s\n' "$file" | sha256sum -c -
python -m pip install --no-deps "$file"
python -m pip install 'numpy==1.23.5' 'scipy==1.10.1' 'gym==0.17.2' 'catkin_pkg==0.5.2' 'matplotlib==3.7.5' 'psutil==5.9.8'
PYTHONPATH="$GITHUB_WORKSPACE/research/lcrm01" python -B -m unittest discover -s research/lcrm01 -p 'test_k4n_sourceonly.py' -v
git init -q "$RUNNER_TEMP/k4n/CausalWorld"
git -C "$RUNNER_TEMP/k4n/CausalWorld" remote add origin https://github.com/rr-learning/CausalWorld.git
git -C "$RUNNER_TEMP/k4n/CausalWorld" fetch --no-tags --depth 1 origin 1045277101a92c506db42704da28f6e7227d401b
git -C "$RUNNER_TEMP/k4n/CausalWorld" checkout --detach -q 1045277101a92c506db42704da28f6e7227d401b
test "$(git -C "$RUNNER_TEMP/k4n/CausalWorld" hash-object causal_world/envs/causalworld.py)" = '6169fcd629e5721e889fbcada52c06e9c2a37b0e'
export PYTHONPATH="$GITHUB_WORKSPACE/research/lcrm01/k4a_overlay:$GITHUB_WORKSPACE/research/lcrm01"
set +e
python -B research/lcrm01/k4n_decision_coreset.py --causalworld-repo "$RUNNER_TEMP/k4n/CausalWorld" --output "$RUNNER_TEMP/k4n/process-a.json" > "$RUNNER_TEMP/k4n/process-a.log" 2>&1
a=$?
python -B research/lcrm01/k4n_decision_coreset.py --causalworld-repo "$RUNNER_TEMP/k4n/CausalWorld" --output "$RUNNER_TEMP/k4n/process-b.json" > "$RUNNER_TEMP/k4n/process-b.log" 2>&1
b=$?
set -e
echo "K4N_PROCESS_A_EXIT=$a K4N_PROCESS_B_EXIT=$b"
cat "$RUNNER_TEMP/k4n/process-a.log" "$RUNNER_TEMP/k4n/process-b.log"
test -s "$RUNNER_TEMP/k4n/process-a.json"
test -s "$RUNNER_TEMP/k4n/process-b.json"
test "$a" -eq 0 && test "$b" -eq 0
python -B research/lcrm01/k4n_compare.py --first "$RUNNER_TEMP/k4n/process-a.json" --second "$RUNNER_TEMP/k4n/process-b.json" --output "$RUNNER_TEMP/k4n/comparison.json"
test -z "$(git -C "$RUNNER_TEMP/k4n/CausalWorld" status --porcelain --untracked-files=no)"
python -B - <<'PY'
import json,os
from pathlib import Path
root=Path(os.environ["RUNNER_TEMP"])/"k4n"
a=json.loads((root/"process-a.json").read_text())
b=json.loads((root/"process-b.json").read_text())
c=json.loads((root/"comparison.json").read_text())
assert a["schema"]==b["schema"]=="mass.lcrm01.k4n.original-fit-decision-fidelity-development.v1"
assert a["FIT_exposures"]==b["FIT_exposures"]==96
assert (a["CHECK_exposures"],a["DEV_exposures"]) in ((0,0),(16,64))
assert a["original_K4L_negative_preserved"] and b["original_K4L_negative_preserved"]
assert a["original_K4M_diagnostic_preserved"] and b["original_K4M_diagnostic_preserved"]
assert not a["scientific_first_use"] and not b["scientific_first_use"]
assert not a["scientific_accepted"] and not b["scientific_accepted"]
assert c["source_and_scientific_records_identical"]
print("K4N_FROZEN_SCIENTIFIC_OUTCOME="+c["result"])
print("K4N_PRIOR_NEGATIVES_PRESERVED=PASS")
PY
