#!/usr/bin/env bash
# K4E hosted public-development runner. Never changes source/authority.
set -euo pipefail
cd "$GITHUB_WORKSPACE"
test "$(git rev-parse '6bff7859187e22b6d71fb1bb8e19927be3e7ef66^')" = '4f0325c5d8f74ac1b54122dc8a7142952f4ad11d'
test "$(git hash-object research/lcrm01/k4e_frozen_reward_ablation.json)" = '64b594f4dbb1bc7d7602394a07a848248f3770c0'
test "$(git hash-object research/lcrm01/k4d_frozen_crossfamily.json)" = '7e195f10eac161eaf9553f4b5e1a839b222386a2'
python -m pip install 'pip==24.0' 'setuptools==69.5.1' 'wheel==0.43.0'
mkdir -p "$RUNNER_TEMP/k4e/wheels"
python -m pip download --only-binary=:all: --no-deps --dest "$RUNNER_TEMP/k4e/wheels" 'pybullet==3.2.5'
file=$(find "$RUNNER_TEMP/k4e/wheels" -maxdepth 1 -name 'pybullet-3.2.5-cp39-cp39-manylinux*.whl' -print -quit)
test -n "$file"
printf '9adcaa00de674a02549949f6f8d51b485bd7a23fbc87a1defb2067e1364f8202  %s\n' "$file" | sha256sum -c -
python -m pip install --no-deps "$file"
python -m pip install 'numpy==1.23.5' 'scipy==1.10.1' 'gym==0.17.2' 'catkin_pkg==0.5.2' 'matplotlib==3.7.5' 'psutil==5.9.8'
PYTHONPATH="$GITHUB_WORKSPACE/research/lcrm01" python -B -m unittest discover -s research/lcrm01 -p 'test_k4e_sourceonly.py' -v
git init -q "$RUNNER_TEMP/k4e/CausalWorld"
git -C "$RUNNER_TEMP/k4e/CausalWorld" remote add origin https://github.com/rr-learning/CausalWorld.git
git -C "$RUNNER_TEMP/k4e/CausalWorld" fetch --no-tags --depth 1 origin 1045277101a92c506db42704da28f6e7227d401b
git -C "$RUNNER_TEMP/k4e/CausalWorld" checkout --detach -q 1045277101a92c506db42704da28f6e7227d401b
test "$(git -C "$RUNNER_TEMP/k4e/CausalWorld" hash-object causal_world/envs/causalworld.py)" = '6169fcd629e5721e889fbcada52c06e9c2a37b0e'
export PYTHONPATH="$GITHUB_WORKSPACE/research/lcrm01/k4a_overlay:$GITHUB_WORKSPACE/research/lcrm01"
set +e
python -B research/lcrm01/k4e_reward_ablation.py --causalworld-repo "$RUNNER_TEMP/k4e/CausalWorld" --output "$RUNNER_TEMP/k4e/process-a.json" > "$RUNNER_TEMP/k4e/process-a.log" 2>&1
a=$?
python -B research/lcrm01/k4e_reward_ablation.py --causalworld-repo "$RUNNER_TEMP/k4e/CausalWorld" --output "$RUNNER_TEMP/k4e/process-b.json" > "$RUNNER_TEMP/k4e/process-b.log" 2>&1
b=$?
set -e
cat "$RUNNER_TEMP/k4e/process-a.log" "$RUNNER_TEMP/k4e/process-b.log"
test -s "$RUNNER_TEMP/k4e/process-a.json"
test -s "$RUNNER_TEMP/k4e/process-b.json"
python -B research/lcrm01/k4e_compare.py --first "$RUNNER_TEMP/k4e/process-a.json" --second "$RUNNER_TEMP/k4e/process-b.json" --output "$RUNNER_TEMP/k4e/cross-process.json"
test "$a" -eq 0
test "$b" -eq 0
test -z "$(git -C "$RUNNER_TEMP/k4e/CausalWorld" status --porcelain --untracked-files=no)"
