#!/usr/bin/env bash
# K4U: original prospective non-controller MiniGrid native first-use study.
set -euo pipefail
cd "$GITHUB_WORKSPACE"
test "$(git rev-parse '8feb93fa1344a0b89e1ab0c0cd143c45864b20b7^')" = 'e542b58c33698d10473b891734af15dca46c12d6'
git merge-base --is-ancestor 8feb93fa1344a0b89e1ab0c0cd143c45864b20b7 HEAD
test "$(git hash-object research/lcrm01/k4u_frozen_native_minigrid.json)" = 'dd3b6a746e0ed5e5804832288b8310647f9c5f62'
test "$(git hash-object research/lcrm01/k4r_frozen_independent_minigrid.json)" = 'cf87447b6eb47b33757a98ea6622ce2ea40bd022'
echo 'K4U_ORIGINAL_SOURCE_PREREGISTRATION=PASS'
mkdir -p "$RUNNER_TEMP/k4u/minigrid" "$RUNNER_TEMP/k4u/yggsrc" "$RUNNER_TEMP/k4u/go/wingless"
python -m pip install 'pip==24.0' 'setuptools==69.5.1' 'wheel==0.43.0'
python -m pip install 'numpy==1.26.4' 'gymnasium==1.1.1' 'pygame-ce==2.5.3'
export PYTHONPATH="$GITHUB_WORKSPACE/research/lcrm01"
python -B -m unittest discover -s research/lcrm01 -p 'test_k4u_sourceonly.py' -v
git init -q "$RUNNER_TEMP/k4u/minigrid"
git -C "$RUNNER_TEMP/k4u/minigrid" remote add origin https://github.com/Farama-Foundation/Minigrid.git
git -C "$RUNNER_TEMP/k4u/minigrid" fetch --no-tags --depth 1 origin 7f5853792ea7f04f75614661006d87fcf949f26d
git -C "$RUNNER_TEMP/k4u/minigrid" checkout --detach -q 7f5853792ea7f04f75614661006d87fcf949f26d
test "$(git -C "$RUNNER_TEMP/k4u/minigrid" hash-object minigrid/envs/empty.py)" = '8810bb0fa156d18475022edd8859b135ef745a5f'
test "$(git -C "$RUNNER_TEMP/k4u/minigrid" hash-object minigrid/envs/fourrooms.py)" = 'd79f007e00f95f48284da66d760872483c02fab2'
test "$(git -C "$RUNNER_TEMP/k4u/minigrid" hash-object minigrid/wrappers.py)" = '1eb2da8fb612653c97f443ff6c7492ed3f1aaa80'
test "$(git -C "$RUNNER_TEMP/k4u/minigrid" hash-object minigrid/minigrid_env.py)" = 'eb29e9a902de0715ab77ec981a2113576d7664fa'
python -m pip install --no-deps -e "$RUNNER_TEMP/k4u/minigrid"
python -B research/lcrm01/k4u_fetch_native_sources.py \
    --wingless-out "$RUNNER_TEMP/k4u/go/wingless/policy.go" \
    --yggdrasil-out "$RUNNER_TEMP/k4u/yggsrc/native_policy.py"
printf 'module k4u\n\ngo 1.25.0\n' > "$RUNNER_TEMP/k4u/go/go.mod"
cp research/lcrm01/k4u_wingless_bridge.go "$RUNNER_TEMP/k4u/go/main.go"
(cd "$RUNNER_TEMP/k4u/go" && go build -trimpath -o "$RUNNER_TEMP/k4u/wingless-bridge" .)
export PYTHONPATH="$RUNNER_TEMP/k4u/yggsrc:$GITHUB_WORKSPACE/research/lcrm01"
# Freeze original source before first heldout event. Both process outputs must
# be unique. No reruns of already consumed DEV due to downstream report drift.
set +e
python -B research/lcrm01/k4u_native_minigrid.py \
  --wingless-binary "$RUNNER_TEMP/k4u/wingless-bridge" \
  --yggdrasil-source-dir "$RUNNER_TEMP/k4u/yggsrc" \
  --output "$RUNNER_TEMP/k4u/process-a.json" \
  > "$RUNNER_TEMP/k4u/process-a.log" 2>&1
a=$?
python -B research/lcrm01/k4u_native_minigrid.py \
  --wingless-binary "$RUNNER_TEMP/k4u/wingless-bridge" \
  --yggdrasil-source-dir "$RUNNER_TEMP/k4u/yggsrc" \
  --output "$RUNNER_TEMP/k4u/process-b.json" \
  > "$RUNNER_TEMP/k4u/process-b.log" 2>&1
b=$?
set -e
echo "K4U_PROCESS_A_EXIT=$a K4U_PROCESS_B_EXIT=$b"
cat "$RUNNER_TEMP/k4u/process-a.log" "$RUNNER_TEMP/k4u/process-b.log"
test "$a" -eq 0 && test "$b" -eq 0
python -B research/lcrm01/k4u_compare.py \
  --first "$RUNNER_TEMP/k4u/process-a.json" \
  --second "$RUNNER_TEMP/k4u/process-b.json" \
  --output "$RUNNER_TEMP/k4u/comparison.json"
test -z "$(git -C "$RUNNER_TEMP/k4u/minigrid" status --porcelain --untracked-files=no)"
python -B - <<'PY'
import json,os
from pathlib import Path
root=Path(os.environ["RUNNER_TEMP"])/"k4u"
a=json.loads((root/"process-a.json").read_text())
b=json.loads((root/"process-b.json").read_text())
c=json.loads((root/"comparison.json").read_text())
assert a["FIT_episodes"]==b["FIT_episodes"]==48
assert a["FIT_public_experience_count"]==b["FIT_public_experience_count"]
assert (a["CHECK_evaluations"],a["DEV_evaluations"]) in ((0,0),(56,112))
assert a["scientific_accepted"] is False and b["scientific_accepted"] is False
assert c["science_identical"] is True
print("K4U_ORIGINAL_SOURCE_FROZEN_AND_IDENTICAL=PASS")
print("K4U_SCIENTIFIC_DISPOSITION="+c["result"])
PY
