#!/usr/bin/env bash
# Public K4H calibration; original K4D/K4F/K4G outcomes remain immutable.
set -euo pipefail
cd "$GITHUB_WORKSPACE"
test "$(git rev-parse 'dd64fbe8b84b5671e048571ac810947a27107801^')" = '07cd3e040013d890d1f00e7de883bb9418053e23'
git merge-base --is-ancestor dd64fbe8b84b5671e048571ac810947a27107801 HEAD
test "$(git hash-object research/lcrm01/k4i_frozen_information_sufficiency.json)" = 'ed7017e274952553512c118b0d36e88892791466'
test "$(git hash-object research/lcrm01/k4h_frozen_varied_worlds.json)" = 'ebed383f858984f34dbb6c14d658f1d0acec86a6'
test "$(git hash-object research/lcrm01/k4g_frozen_action_identifiability.json)" = 'a0b610d21b9dd81894f4aeded282a8a110077fb4'
test "$(git hash-object research/lcrm01/k4f_frozen_interactive_learning.json)" = '275bd301abe88c3d33aef2679bc3775445657603'
echo 'a6e97b95fcfa3fc74e9b9fa28ffc22640d99c8fc0f4da31a10336c0f6906e270  research/lcrm01/k4a_control_replay.py' | sha256sum -c -
echo '1a6169bba4f77bb28519766184636c89bfcdc5b5ab23485475e64de474ea09bb  research/lcrm01/k4b_replay_state_repair.py' | sha256sum -c -
python -m pip install 'pip==24.0' 'setuptools==69.5.1' 'wheel==0.43.0'
mkdir -p "$RUNNER_TEMP/k4i/wheels"
python -m pip download --only-binary=:all: --no-deps --dest "$RUNNER_TEMP/k4i/wheels" 'pybullet==3.2.5'
file=$(find "$RUNNER_TEMP/k4i/wheels" -maxdepth 1 -type f -name 'pybullet-3.2.5-cp39-cp39-manylinux*.whl' -print -quit)
test -n "$file"
printf '9adcaa00de674a02549949f6f8d51b485bd7a23fbc87a1defb2067e1364f8202  %s\n' "$file" | sha256sum -c -
python -m pip install --no-deps "$file"
python -m pip install 'numpy==1.23.5' 'scipy==1.10.1' 'gym==0.17.2' 'catkin_pkg==0.5.2' 'matplotlib==3.7.5' 'psutil==5.9.8'
PYTHONPATH="$GITHUB_WORKSPACE/research/lcrm01" python -B -m unittest discover -s research/lcrm01 -p 'test_k4i_sourceonly.py' -v
git init -q "$RUNNER_TEMP/k4i/CausalWorld"
git -C "$RUNNER_TEMP/k4i/CausalWorld" remote add origin https://github.com/rr-learning/CausalWorld.git
git -C "$RUNNER_TEMP/k4i/CausalWorld" fetch --no-tags --depth 1 origin 1045277101a92c506db42704da28f6e7227d401b
git -C "$RUNNER_TEMP/k4i/CausalWorld" checkout --detach -q 1045277101a92c506db42704da28f6e7227d401b
test "$(git -C "$RUNNER_TEMP/k4i/CausalWorld" hash-object causal_world/envs/causalworld.py)" = '6169fcd629e5721e889fbcada52c06e9c2a37b0e'
export PYTHONPATH="$GITHUB_WORKSPACE/research/lcrm01/k4a_overlay:$GITHUB_WORKSPACE/research/lcrm01"
python -B research/lcrm01/k4i_information_sufficiency.py --causalworld-repo "$RUNNER_TEMP/k4i/CausalWorld" --output "$RUNNER_TEMP/k4i/original-fit-information.json" 2>&1 | tee "$RUNNER_TEMP/k4i/original-fit-information.log"
test -z "$(git -C "$RUNNER_TEMP/k4i/CausalWorld" status --porcelain --untracked-files=no)"
python -B - <<'PY'
import json,os
from pathlib import Path
r=json.loads((Path(os.environ["RUNNER_TEMP"])/"k4i/original-fit-information.json").read_text())
assert r["schema"]=="mass.lcrm01.k4i.real-fit-information-source-and-context-controls.v1"
assert r["FIT_exposures"]==96
assert (r["CHECK_exposures"],r["DEV_exposures"]) in ((0,0),(16,32))
assert r["K4H_negative_preserved"] is True and r["K4F_negative_preserved"] is True
assert not r["original_first_use"] and not r["scientific_accepted"]
print("K4I_COHORT_CUSTODY_PASS=TRUE")
print("K4I_VERDICT="+r["result"])
PY
