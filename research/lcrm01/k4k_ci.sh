#!/usr/bin/env bash
# Public K4K compression measurement; original K4D/K4F/K4G outcomes remain immutable.
set -euo pipefail
cd "$GITHUB_WORKSPACE"
test "$(git rev-parse '19ac743e27a4a4333ab7f476df812cebeadd9973^')" = 'b6e19f3321a47d0fac93924c36f55d5fd690169d'
git merge-base --is-ancestor 19ac743e27a4a4333ab7f476df812cebeadd9973 HEAD
test "$(git hash-object research/lcrm01/k4k_frozen_compression.json)" = 'c72d10ac280291ad2a66551cfc71c560ee111537'
test "$(git hash-object research/lcrm01/k4j_frozen_replication.json)" = '8ac57119963f8766f5bb82ecd0597587927a92e4'
test "$(git hash-object research/lcrm01/k4i_frozen_information_sufficiency.json)" = 'ed7017e274952553512c118b0d36e88892791466'
test "$(git hash-object research/lcrm01/k4h_frozen_varied_worlds.json)" = 'ebed383f858984f34dbb6c14d658f1d0acec86a6'
test "$(git hash-object research/lcrm01/k4g_frozen_action_identifiability.json)" = 'a0b610d21b9dd81894f4aeded282a8a110077fb4'
test "$(git hash-object research/lcrm01/k4f_frozen_interactive_learning.json)" = '275bd301abe88c3d33aef2679bc3775445657603'
echo 'a6e97b95fcfa3fc74e9b9fa28ffc22640d99c8fc0f4da31a10336c0f6906e270  research/lcrm01/k4a_control_replay.py' | sha256sum -c -
echo '1a6169bba4f77bb28519766184636c89bfcdc5b5ab23485475e64de474ea09bb  research/lcrm01/k4b_replay_state_repair.py' | sha256sum -c -
python -m pip install 'pip==24.0' 'setuptools==69.5.1' 'wheel==0.43.0'
mkdir -p "$RUNNER_TEMP/k4k/wheels"
python -m pip download --only-binary=:all: --no-deps --dest "$RUNNER_TEMP/k4k/wheels" 'pybullet==3.2.5'
file=$(find "$RUNNER_TEMP/k4k/wheels" -maxdepth 1 -type f -name 'pybullet-3.2.5-cp39-cp39-manylinux*.whl' -print -quit)
test -n "$file"
printf '9adcaa00de674a02549949f6f8d51b485bd7a23fbc87a1defb2067e1364f8202  %s\n' "$file" | sha256sum -c -
python -m pip install --no-deps "$file"
python -m pip install 'numpy==1.23.5' 'scipy==1.10.1' 'gym==0.17.2' 'catkin_pkg==0.5.2' 'matplotlib==3.7.5' 'psutil==5.9.8'
PYTHONPATH="$GITHUB_WORKSPACE/research/lcrm01" python -B -m unittest discover -s research/lcrm01 -p 'test_k4k_sourceonly.py' -v
git init -q "$RUNNER_TEMP/k4k/CausalWorld"
git -C "$RUNNER_TEMP/k4k/CausalWorld" remote add origin https://github.com/rr-learning/CausalWorld.git
git -C "$RUNNER_TEMP/k4k/CausalWorld" fetch --no-tags --depth 1 origin 1045277101a92c506db42704da28f6e7227d401b
git -C "$RUNNER_TEMP/k4k/CausalWorld" checkout --detach -q 1045277101a92c506db42704da28f6e7227d401b
test "$(git -C "$RUNNER_TEMP/k4k/CausalWorld" hash-object causal_world/envs/causalworld.py)" = '6169fcd629e5721e889fbcada52c06e9c2a37b0e'
export PYTHONPATH="$GITHUB_WORKSPACE/research/lcrm01/k4a_overlay:$GITHUB_WORKSPACE/research/lcrm01"
# Each process independently collects frozen FIT and, only if informative, heldout episodes.
# Preserve failure exit codes, original JSON and logs from both attempts.
set +e
python -B research/lcrm01/k4k_compression.py --causalworld-repo "$RUNNER_TEMP/k4k/CausalWorld" --output "$RUNNER_TEMP/k4k/process-a.json" > "$RUNNER_TEMP/k4k/process-a.log" 2>&1
a=$?
python -B research/lcrm01/k4k_compression.py --causalworld-repo "$RUNNER_TEMP/k4k/CausalWorld" --output "$RUNNER_TEMP/k4k/process-b.json" > "$RUNNER_TEMP/k4k/process-b.log" 2>&1
b=$?
set -e
echo "K4K_PROCESS_A_EXIT=$a K4K_PROCESS_B_EXIT=$b"
cat "$RUNNER_TEMP/k4k/process-a.log" "$RUNNER_TEMP/k4k/process-b.log"
test -s "$RUNNER_TEMP/k4k/process-a.json"
test -s "$RUNNER_TEMP/k4k/process-b.json"
python -B research/lcrm01/k4k_compare.py --first "$RUNNER_TEMP/k4k/process-a.json" --second "$RUNNER_TEMP/k4k/process-b.json" --output "$RUNNER_TEMP/k4k/comparison.json"
test "$a" -eq 0 && test "$b" -eq 0
test -z "$(git -C "$RUNNER_TEMP/k4k/CausalWorld" status --porcelain --untracked-files=no)"
python -B - <<'PY'
import json,os
from pathlib import Path
root=Path(os.environ["RUNNER_TEMP"])/"k4k"
a=json.loads((root/"process-a.json").read_text())
b=json.loads((root/"process-b.json").read_text())
c=json.loads((root/"comparison.json").read_text())
assert a["schema"]==b["schema"]=="mass.lcrm01.k4k.original-cost-quality-development.v1"
assert a["FIT_exposures"]==b["FIT_exposures"]==96
assert (a["CHECK_exposures"],a["DEV_exposures"]) in ((0,0),(16,32))
assert not a["scientific_first_use"] and not b["scientific_first_use"]
assert not a["scientific_accepted"] and not b["scientific_accepted"]
assert a["original_K4J_preserved"] is True and b["original_K4J_preserved"] is True
assert c["exact_source_science_agreement"]
print("K4K_COMPRESSOR_VERDICT="+c["result"])
print("K4K_ORIGINAL_NEGATIVES_UNCHANGED=TRUE")
PY
