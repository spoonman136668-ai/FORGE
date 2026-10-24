#!/usr/bin/env bash
set -euo pipefail
cd "$GITHUB_WORKSPACE"
test "$(git rev-parse '996202c0f2348b8a4dce894daa5d88d2c816c1c1^')" = '0bb78beaa07a25a021513548976f765824e6ca22'
git merge-base --is-ancestor 996202c0f2348b8a4dce894daa5d88d2c816c1c1 HEAD
test "$(git hash-object research/lcrm01/k4x_frozen_curriculum_intervention.json)" = '664f0c92070ed5bedc70ba934edce9adaf9cdb4f'
test "$(git hash-object research/lcrm01/k4w_frozen_failure_attribution.json)" = '9a37039e2a9db8bf269b78fcc9cf1642e3c6978c'
echo 'K4X_FROZEN_PROSPECTIVE_IDENTITIES=PASS'
mkdir -p "$RUNNER_TEMP/k4x/minigrid" "$RUNNER_TEMP/k4x/yggsrc" "$RUNNER_TEMP/k4x/go/wingless"
python -m pip install 'pip==24.0' 'setuptools==69.5.1' 'wheel==0.43.0'
python -m pip install 'numpy==1.26.4' 'gymnasium==1.1.1' 'pygame-ce==2.5.3'
export PYTHONPATH="$GITHUB_WORKSPACE/research/lcrm01"
python -B -m unittest discover -s research/lcrm01 -p 'test_k4x_sourceonly.py' -v
git init -q "$RUNNER_TEMP/k4x/minigrid"
git -C "$RUNNER_TEMP/k4x/minigrid" remote add origin https://github.com/Farama-Foundation/Minigrid.git
git -C "$RUNNER_TEMP/k4x/minigrid" fetch --no-tags --depth 1 origin 7f5853792ea7f04f75614661006d87fcf949f26d
git -C "$RUNNER_TEMP/k4x/minigrid" checkout --detach -q 7f5853792ea7f04f75614661006d87fcf949f26d
test "$(git -C "$RUNNER_TEMP/k4x/minigrid" hash-object minigrid/envs/empty.py)" = '8810bb0fa156d18475022edd8859b135ef745a5f'
test "$(git -C "$RUNNER_TEMP/k4x/minigrid" hash-object minigrid/envs/fourrooms.py)" = 'd79f007e00f95f48284da66d760872483c02fab2'
test "$(git -C "$RUNNER_TEMP/k4x/minigrid" hash-object minigrid/wrappers.py)" = '1eb2da8fb612653c97f443ff6c7492ed3f1aaa80'
test "$(git -C "$RUNNER_TEMP/k4x/minigrid" hash-object minigrid/minigrid_env.py)" = 'eb29e9a902de0715ab77ec981a2113576d7664fa'
python -m pip install --no-deps -e "$RUNNER_TEMP/k4x/minigrid"
python -B research/lcrm01/k4u_fetch_native_sources.py \
    --wingless-out "$RUNNER_TEMP/k4x/go/wingless/policy.go" \
    --yggdrasil-out "$RUNNER_TEMP/k4x/yggsrc/native_policy.py"
printf 'module k4u\n\ngo 1.25.0\n' > "$RUNNER_TEMP/k4x/go/go.mod"
cp research/lcrm01/k4u_wingless_bridge.go "$RUNNER_TEMP/k4x/go/main.go"
(cd "$RUNNER_TEMP/k4x/go" && go build -trimpath -o "$RUNNER_TEMP/k4x/wingless-bridge" .)
export PYTHONPATH="$RUNNER_TEMP/k4x/yggsrc:$GITHUB_WORKSPACE/research/lcrm01"
set +e
python -B research/lcrm01/k4x_curriculum_intervention.py \
 --go-binary "$RUNNER_TEMP/k4x/wingless-bridge" \
 --ygg-source-dir "$RUNNER_TEMP/k4x/yggsrc" \
 --output "$RUNNER_TEMP/k4x/process-a.json" \
 > "$RUNNER_TEMP/k4x/process-a.log" 2>&1
a=$?
python -B research/lcrm01/k4x_curriculum_intervention.py \
 --go-binary "$RUNNER_TEMP/k4x/wingless-bridge" \
 --ygg-source-dir "$RUNNER_TEMP/k4x/yggsrc" \
 --output "$RUNNER_TEMP/k4x/process-b.json" \
 > "$RUNNER_TEMP/k4x/process-b.log" 2>&1
b=$?
set -e
echo "K4X_PROCESS_A_EXIT=$a K4X_PROCESS_B_EXIT=$b"
cat "$RUNNER_TEMP/k4x/process-a.log" "$RUNNER_TEMP/k4x/process-b.log"
test "$a" -eq 0 && test "$b" -eq 0
python -B research/lcrm01/k4x_compare.py \
 --first "$RUNNER_TEMP/k4x/process-a.json" \
 --second "$RUNNER_TEMP/k4x/process-b.json" \
 --output "$RUNNER_TEMP/k4x/comparison.json"
test -z "$(git -C "$RUNNER_TEMP/k4x/minigrid" status --porcelain --untracked-files=no)"
python -B - <<'PY'
import json,os,pathlib
root=pathlib.Path(os.environ["RUNNER_TEMP"])/"k4x"
a=json.loads((root/"process-a.json").read_text())
b=json.loads((root/"process-b.json").read_text())
c=json.loads((root/"comparison.json").read_text())
assert all(a["FIT"][mode]["source_balance"][fam]["public_steps"]==6000
      for mode in ("random_equal_budget","public_bfs_demonstration_equal_budget")
      for fam in ("empty","fourrooms"))
assert a["scientific_first_use"] is False and a["scientific_accepted"] is False
assert b["scientific_first_use"] is False and b["scientific_accepted"] is False
assert c["exact_original_science_agreement"] is True
assert c["scientific_accepted"] is False
print("K4X_FROZEN_SOURCE_AND_SCIENTIFIC_NEGATIVES_PRESERVED=PASS")
print("K4X_PROSPECTIVE_CURRICULUM_RESULT="+c["result"])
PY
