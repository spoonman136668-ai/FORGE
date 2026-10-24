#!/usr/bin/env bash
set -euo pipefail
cd "$GITHUB_WORKSPACE"
test "$(git rev-parse '7c95699b0557dab6441725ce54b2170fda85a4e0^')" = '3218051c65f8c0e293513971a3ea3148e935a591'
git merge-base --is-ancestor 7c95699b0557dab6441725ce54b2170fda85a4e0 HEAD
test "$(git hash-object research/lcrm01/k4l_frozen_multicontext.json)" = 'c69aec62a50417947f3ad6e9615a2afc55625033'
test "$(git hash-object research/lcrm01/k4k_frozen_compression.json)" = 'c72d10ac280291ad2a66551cfc71c560ee111537'
test "$(git hash-object research/lcrm01/k4j_frozen_replication.json)" = '8ac57119963f8766f5bb82ecd0597587927a92e4'
python -m pip install 'pip==24.0' 'setuptools==69.5.1' 'wheel==0.43.0'
mkdir -p "$RUNNER_TEMP/k4l/wheels"
python -m pip download --only-binary=:all: --no-deps --dest "$RUNNER_TEMP/k4l/wheels" 'pybullet==3.2.5'
file=$(find "$RUNNER_TEMP/k4l/wheels" -maxdepth 1 -name 'pybullet-3.2.5-cp39-cp39-manylinux*.whl' -print -quit)
test -n "$file"
printf '9adcaa00de674a02549949f6f8d51b485bd7a23fbc87a1defb2067e1364f8202  %s\n' "$file" | sha256sum -c -
python -m pip install --no-deps "$file"
python -m pip install 'numpy==1.23.5' 'scipy==1.10.1' 'gym==0.17.2' 'catkin_pkg==0.5.2' 'matplotlib==3.7.5' 'psutil==5.9.8'
PYTHONPATH="$GITHUB_WORKSPACE/research/lcrm01" python -B -m unittest discover -s research/lcrm01 -p 'test_k4l_sourceonly.py' -v
git init -q "$RUNNER_TEMP/k4l/CausalWorld"
git -C "$RUNNER_TEMP/k4l/CausalWorld" remote add origin https://github.com/rr-learning/CausalWorld.git
git -C "$RUNNER_TEMP/k4l/CausalWorld" fetch --no-tags --depth 1 origin 1045277101a92c506db42704da28f6e7227d401b
git -C "$RUNNER_TEMP/k4l/CausalWorld" checkout --detach -q 1045277101a92c506db42704da28f6e7227d401b
test "$(git -C "$RUNNER_TEMP/k4l/CausalWorld" hash-object causal_world/envs/causalworld.py)" = '6169fcd629e5721e889fbcada52c06e9c2a37b0e'
export PYTHONPATH="$GITHUB_WORKSPACE/research/lcrm01/k4a_overlay:$GITHUB_WORKSPACE/research/lcrm01"
set +e
python -B research/lcrm01/k4l_multicontext.py --causalworld-repo "$RUNNER_TEMP/k4l/CausalWorld" --output "$RUNNER_TEMP/k4l/process-a.json" > "$RUNNER_TEMP/k4l/process-a.log" 2>&1
a=$?
python -B research/lcrm01/k4l_multicontext.py --causalworld-repo "$RUNNER_TEMP/k4l/CausalWorld" --output "$RUNNER_TEMP/k4l/process-b.json" > "$RUNNER_TEMP/k4l/process-b.log" 2>&1
b=$?
set -e
echo "PROCESS_A_EXIT=$a PROCESS_B_EXIT=$b"
cat "$RUNNER_TEMP/k4l/process-a.log" "$RUNNER_TEMP/k4l/process-b.log"
test "$a" -eq 0 && test "$b" -eq 0
python -B research/lcrm01/k4l_compare.py --first "$RUNNER_TEMP/k4l/process-a.json" --second "$RUNNER_TEMP/k4l/process-b.json" --output "$RUNNER_TEMP/k4l/comparison.json"
test -z "$(git -C "$RUNNER_TEMP/k4l/CausalWorld" status --porcelain --untracked-files=no)"
