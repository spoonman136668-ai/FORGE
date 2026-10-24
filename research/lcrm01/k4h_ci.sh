#!/usr/bin/env bash
# Public K4H calibration; original K4D/K4F/K4G outcomes remain immutable.
set -euo pipefail
cd "$GITHUB_WORKSPACE"
test "$(git rev-parse 'e54040aec4e5a0bf6cada250fc27da8008befa08^')" = '26ef0fb5166e15a756ef0fdb96b7830b03c6da52'
git merge-base --is-ancestor e54040aec4e5a0bf6cada250fc27da8008befa08 HEAD
test "$(git hash-object research/lcrm01/k4h_frozen_varied_worlds.json)" = 'ebed383f858984f34dbb6c14d658f1d0acec86a6'
test "$(git hash-object research/lcrm01/k4g_frozen_action_identifiability.json)" = 'a0b610d21b9dd81894f4aeded282a8a110077fb4'
test "$(git hash-object research/lcrm01/k4f_frozen_interactive_learning.json)" = '275bd301abe88c3d33aef2679bc3775445657603'
echo 'a6e97b95fcfa3fc74e9b9fa28ffc22640d99c8fc0f4da31a10336c0f6906e270  research/lcrm01/k4a_control_replay.py' | sha256sum -c -
echo '1a6169bba4f77bb28519766184636c89bfcdc5b5ab23485475e64de474ea09bb  research/lcrm01/k4b_replay_state_repair.py' | sha256sum -c -
python -m pip install 'pip==24.0' 'setuptools==69.5.1' 'wheel==0.43.0'
mkdir -p "$RUNNER_TEMP/k4h/wheels"
python -m pip download --only-binary=:all: --no-deps --dest "$RUNNER_TEMP/k4h/wheels" 'pybullet==3.2.5'
file=$(find "$RUNNER_TEMP/k4h/wheels" -maxdepth 1 -type f -name 'pybullet-3.2.5-cp39-cp39-manylinux*.whl' -print -quit)
test -n "$file"
printf '9adcaa00de674a02549949f6f8d51b485bd7a23fbc87a1defb2067e1364f8202  %s\n' "$file" | sha256sum -c -
python -m pip install --no-deps "$file"
python -m pip install 'numpy==1.23.5' 'scipy==1.10.1' 'gym==0.17.2' 'catkin_pkg==0.5.2' 'matplotlib==3.7.5' 'psutil==5.9.8'
PYTHONPATH="$GITHUB_WORKSPACE/research/lcrm01" python -B -m unittest discover -s research/lcrm01 -p 'test_k4h_sourceonly.py' -v
git init -q "$RUNNER_TEMP/k4h/CausalWorld"
git -C "$RUNNER_TEMP/k4h/CausalWorld" remote add origin https://github.com/rr-learning/CausalWorld.git
git -C "$RUNNER_TEMP/k4h/CausalWorld" fetch --no-tags --depth 1 origin 1045277101a92c506db42704da28f6e7227d401b
git -C "$RUNNER_TEMP/k4h/CausalWorld" checkout --detach -q 1045277101a92c506db42704da28f6e7227d401b
test "$(git -C "$RUNNER_TEMP/k4h/CausalWorld" hash-object causal_world/envs/causalworld.py)" = '6169fcd629e5721e889fbcada52c06e9c2a37b0e'
export PYTHONPATH="$GITHUB_WORKSPACE/research/lcrm01/k4a_overlay:$GITHUB_WORKSPACE/research/lcrm01"
python -B research/lcrm01/k4h_varied_worlds.py --causalworld-repo "$RUNNER_TEMP/k4h/CausalWorld" --output "$RUNNER_TEMP/k4h/original-varied-worlds.json" 2>&1 | tee "$RUNNER_TEMP/k4h/original-varied-worlds.log"
test -z "$(git -C "$RUNNER_TEMP/k4h/CausalWorld" status --porcelain --untracked-files=no)"
python -B - <<'PY'
import json,os
from pathlib import Path
r=json.loads((Path(os.environ["RUNNER_TEMP"])/"k4h/original-varied-worlds.json").read_text())
assert r["schema"]=="mass.lcrm01.k4h.varied-public-worlds-development.v1"
assert r["FIT_exposures"]==32 and r["CHECK_exposures"]==8 and r["DEV_exposures"]==16
assert r["checkpoint_predictions_retained"]
assert not r["original_first_use"] and not r["scientific_accepted"]
assert r["K4F_original_negative_preserved"] and r["K4G_context_limitation_preserved"]
print("K4H_SOURCE_VARIATION="+r["calibration"]["source_variation"])
print("K4H_CONTEXTUAL_TRANSFER="+r["calibration"]["contextual_generalization"])
print("K4H_ORIGINAL_PUBLIC_EVIDENCE_RETAINED=TRUE")
PY
