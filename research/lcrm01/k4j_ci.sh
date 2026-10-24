#!/usr/bin/env bash
# Public K4H calibration; original K4D/K4F/K4G outcomes remain immutable.
set -euo pipefail
cd "$GITHUB_WORKSPACE"
test "$(git rev-parse '5ccdf5a7995e8c71a0166935243556550782daf2^')" = 'a25d2ecd3548049a5f8d1a0fbb7375de27fffcd5'
git merge-base --is-ancestor 5ccdf5a7995e8c71a0166935243556550782daf2 HEAD
test "$(git hash-object research/lcrm01/k4j_frozen_replication.json)" = '8ac57119963f8766f5bb82ecd0597587927a92e4'
test "$(git hash-object research/lcrm01/k4i_frozen_information_sufficiency.json)" = 'ed7017e274952553512c118b0d36e88892791466'
test "$(git hash-object research/lcrm01/k4h_frozen_varied_worlds.json)" = 'ebed383f858984f34dbb6c14d658f1d0acec86a6'
test "$(git hash-object research/lcrm01/k4g_frozen_action_identifiability.json)" = 'a0b610d21b9dd81894f4aeded282a8a110077fb4'
test "$(git hash-object research/lcrm01/k4f_frozen_interactive_learning.json)" = '275bd301abe88c3d33aef2679bc3775445657603'
echo 'a6e97b95fcfa3fc74e9b9fa28ffc22640d99c8fc0f4da31a10336c0f6906e270  research/lcrm01/k4a_control_replay.py' | sha256sum -c -
echo '1a6169bba4f77bb28519766184636c89bfcdc5b5ab23485475e64de474ea09bb  research/lcrm01/k4b_replay_state_repair.py' | sha256sum -c -
python -m pip install 'pip==24.0' 'setuptools==69.5.1' 'wheel==0.43.0'
mkdir -p "$RUNNER_TEMP/k4j/wheels"
python -m pip download --only-binary=:all: --no-deps --dest "$RUNNER_TEMP/k4j/wheels" 'pybullet==3.2.5'
file=$(find "$RUNNER_TEMP/k4j/wheels" -maxdepth 1 -type f -name 'pybullet-3.2.5-cp39-cp39-manylinux*.whl' -print -quit)
test -n "$file"
printf '9adcaa00de674a02549949f6f8d51b485bd7a23fbc87a1defb2067e1364f8202  %s\n' "$file" | sha256sum -c -
python -m pip install --no-deps "$file"
python -m pip install 'numpy==1.23.5' 'scipy==1.10.1' 'gym==0.17.2' 'catkin_pkg==0.5.2' 'matplotlib==3.7.5' 'psutil==5.9.8'
PYTHONPATH="$GITHUB_WORKSPACE/research/lcrm01" python -B -m unittest discover -s research/lcrm01 -p 'test_k4j_sourceonly.py' -v
git init -q "$RUNNER_TEMP/k4j/CausalWorld"
git -C "$RUNNER_TEMP/k4j/CausalWorld" remote add origin https://github.com/rr-learning/CausalWorld.git
git -C "$RUNNER_TEMP/k4j/CausalWorld" fetch --no-tags --depth 1 origin 1045277101a92c506db42704da28f6e7227d401b
git -C "$RUNNER_TEMP/k4j/CausalWorld" checkout --detach -q 1045277101a92c506db42704da28f6e7227d401b
test "$(git -C "$RUNNER_TEMP/k4j/CausalWorld" hash-object causal_world/envs/causalworld.py)" = '6169fcd629e5721e889fbcada52c06e9c2a37b0e'
export PYTHONPATH="$GITHUB_WORKSPACE/research/lcrm01/k4a_overlay:$GITHUB_WORKSPACE/research/lcrm01"
# Each process independently collects frozen FIT and, only if informative, heldout episodes.
# Preserve failure exit codes, original JSON and logs from both attempts.
set +e
python -B research/lcrm01/k4j_replicate.py --causalworld-repo "$RUNNER_TEMP/k4j/CausalWorld" --output "$RUNNER_TEMP/k4j/process-a.json" > "$RUNNER_TEMP/k4j/process-a.log" 2>&1
a=$?
python -B research/lcrm01/k4j_replicate.py --causalworld-repo "$RUNNER_TEMP/k4j/CausalWorld" --output "$RUNNER_TEMP/k4j/process-b.json" > "$RUNNER_TEMP/k4j/process-b.log" 2>&1
b=$?
set -e
echo "K4J_PROCESS_A_EXIT=$a K4J_PROCESS_B_EXIT=$b"
cat "$RUNNER_TEMP/k4j/process-a.log" "$RUNNER_TEMP/k4j/process-b.log"
test -s "$RUNNER_TEMP/k4j/process-a.json"
test -s "$RUNNER_TEMP/k4j/process-b.json"
python -B research/lcrm01/k4j_compare.py --first "$RUNNER_TEMP/k4j/process-a.json" --second "$RUNNER_TEMP/k4j/process-b.json" --output "$RUNNER_TEMP/k4j/comparison.json"
test "$a" -eq 0 && test "$b" -eq 0
test -z "$(git -C "$RUNNER_TEMP/k4j/CausalWorld" status --porcelain --untracked-files=no)"
python -B - <<'PY'
import json,os
from pathlib import Path
root=Path(os.environ["RUNNER_TEMP"])/"k4j"
a=json.loads((root/"process-a.json").read_text())
b=json.loads((root/"process-b.json").read_text())
z=json.loads((root/"comparison.json").read_text())
assert a["schema"]==b["schema"]=="mass.lcrm01.k4j.original-independent-process-public-replication.v1"
assert a["FIT_exposures"]==b["FIT_exposures"]==96
assert (a["CHECK_exposures"],a["DEV_exposures"]) in ((0,0),(16,32))
assert a["scientific_first_use"] is False and b["scientific_first_use"] is False
assert z["exact_original_evidence_match"] is True
assert z["independent_host_replicated"] is False
print("K4J_BOUNDED_VERDICT="+z["result"])
print("K4J_ORIGINAL_NEGATIVE_HISTORY_PRESERVED=TRUE")
PY
