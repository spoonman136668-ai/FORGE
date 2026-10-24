#!/usr/bin/env bash
# K4G: original PUBLIC action-consequence calibration; no scientific acceptance.
set -euo pipefail
cd "$GITHUB_WORKSPACE"
test "$(git rev-parse '650b9d8700699842685fe9c89b0f00a4dc4bdb4b^')" = '9413d309aeec85a82679637a020bef53f98cba43'
git merge-base --is-ancestor 650b9d8700699842685fe9c89b0f00a4dc4bdb4b HEAD
test "$(git hash-object research/lcrm01/k4g_frozen_action_identifiability.json)" = 'a0b610d21b9dd81894f4aeded282a8a110077fb4'
test "$(git hash-object research/lcrm01/k4f_frozen_interactive_learning.json)" = '275bd301abe88c3d33aef2679bc3775445657603'
test "$(git hash-object research/lcrm01/k4e_frozen_reward_ablation.json)" = '64b594f4dbb1bc7d7602394a07a848248f3770c0'
echo 'a6e97b95fcfa3fc74e9b9fa28ffc22640d99c8fc0f4da31a10336c0f6906e270  research/lcrm01/k4a_control_replay.py' | sha256sum -c -
echo '1a6169bba4f77bb28519766184636c89bfcdc5b5ab23485475e64de474ea09bb  research/lcrm01/k4b_replay_state_repair.py' | sha256sum -c -
python -m pip install 'pip==24.0' 'setuptools==69.5.1' 'wheel==0.43.0'
mkdir -p "$RUNNER_TEMP/k4g/wheels"
python -m pip download --only-binary=:all: --no-deps --dest "$RUNNER_TEMP/k4g/wheels" 'pybullet==3.2.5'
file=$(find "$RUNNER_TEMP/k4g/wheels" -maxdepth 1 -type f -name 'pybullet-3.2.5-cp39-cp39-manylinux*.whl' -print -quit)
test -n "$file"
printf '9adcaa00de674a02549949f6f8d51b485bd7a23fbc87a1defb2067e1364f8202  %s\n' "$file" | sha256sum -c -
python -m pip install --no-deps "$file"
python -m pip install 'numpy==1.23.5' 'scipy==1.10.1' 'gym==0.17.2' 'catkin_pkg==0.5.2' 'matplotlib==3.7.5' 'psutil==5.9.8'
PYTHONPATH="$GITHUB_WORKSPACE/research/lcrm01" python -B -m unittest discover -s research/lcrm01 -p 'test_k4g_sourceonly.py' -v
git init -q "$RUNNER_TEMP/k4g/CausalWorld"
git -C "$RUNNER_TEMP/k4g/CausalWorld" remote add origin https://github.com/rr-learning/CausalWorld.git
git -C "$RUNNER_TEMP/k4g/CausalWorld" fetch --no-tags --depth 1 origin 1045277101a92c506db42704da28f6e7227d401b
git -C "$RUNNER_TEMP/k4g/CausalWorld" checkout --detach -q 1045277101a92c506db42704da28f6e7227d401b
test "$(git -C "$RUNNER_TEMP/k4g/CausalWorld" hash-object causal_world/envs/causalworld.py)" = '6169fcd629e5721e889fbcada52c06e9c2a37b0e'
export PYTHONPATH="$GITHUB_WORKSPACE/research/lcrm01/k4a_overlay:$GITHUB_WORKSPACE/research/lcrm01"
python -B research/lcrm01/k4g_action_identifiability.py --causalworld-repo "$RUNNER_TEMP/k4g/CausalWorld" --output "$RUNNER_TEMP/k4g/original-public-dev.json" 2>&1 | tee "$RUNNER_TEMP/k4g/original-public-dev.log"
test -z "$(git -C "$RUNNER_TEMP/k4g/CausalWorld" status --porcelain --untracked-files=no)"
python -B - <<'PY'
import json,os
from pathlib import Path
r=json.loads((Path(os.environ["RUNNER_TEMP"])/"k4g/original-public-dev.json").read_text())
assert r["schema"]=="mass.lcrm01.k4g.original-action-discrimination-dev.v1"
assert r["FIT_exposures"]==32 and r["CHECK_exposures"]==16 and r["DEV_exposures"]==32
assert r["first_use_authorized"] is False and r["scientific_accepted"] is False
assert r["original_K4F_NO_GO_preserved"] is True
print("K4G_AUTHENTIC_PUBLIC_EVIDENCE=RETAINED")
print("K4G_VERDICT="+r["calibration"]["disposition"])
PY
