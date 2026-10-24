#!/usr/bin/env bash
set -euo pipefail
cd "$GITHUB_WORKSPACE"
test "$(git rev-parse 'db187355c21dd68d932b500211bc961ee44f5f8^')" = '93a3cd37a386da149a22d16d5b2c33d1ce61ef17'
git merge-base --is-ancestor db187355c21dd68d932b500211bc961ee44f5f8 HEAD
test "$(git hash-object research/lcrm01/k4r_frozen_independent_minigrid.json)" = 'cf87447b6eb47b33757a98ea6622ce2ea40bd022'
test "$(git hash-object research/lcrm01/k4q_frozen_causal_observability.json)" = 'da09b5179d6459ad108b1f618cf1f4c2f1f7a581'
python -m pip install 'pip==24.0' 'setuptools==69.5.1' 'wheel==0.43.0'
python -m pip install 'numpy==1.26.4' 'gymnasium==1.1.1' 'pygame-ce==2.5.3'
git init -q "$RUNNER_TEMP/k4r/Minigrid"
git -C "$RUNNER_TEMP/k4r/Minigrid" remote add origin https://github.com/Farama-Foundation/Minigrid.git
git -C "$RUNNER_TEMP/k4r/Minigrid" fetch --no-tags --depth 1 origin 7f5853792ea7f04f75614661006d87fcf949f26d
git -C "$RUNNER_TEMP/k4r/Minigrid" checkout --detach -q 7f5853792ea7f04f75614661006d87fcf949f26d
test "$(git -C "$RUNNER_TEMP/k4r/Minigrid" hash-object minigrid/envs/empty.py)" = '8810bb0fa156d18475022edd8859b135ef745a5f'
test "$(git -C "$RUNNER_TEMP/k4r/Minigrid" hash-object minigrid/envs/fourrooms.py)" = 'd79f007e00f95f48284da66d760872483c02fab2'
test "$(git -C "$RUNNER_TEMP/k4r/Minigrid" hash-object minigrid/wrappers.py)" = '1eb2da8fb612653c97f443ff6c7492ed3f1aaa80'
test "$(git -C "$RUNNER_TEMP/k4r/Minigrid" hash-object minigrid/minigrid_env.py)" = 'eb29e9a902de0715ab77ec981a2113576d7664fa'
python -m pip install --no-deps -e "$RUNNER_TEMP/k4r/Minigrid"
PYTHONPATH=research/lcrm01 python -B -m unittest discover -s research/lcrm01 -p 'test_k4r_sourceonly.py' -v
export PYTHONPATH="$GITHUB_WORKSPACE/research/lcrm01"
set +e
python -B research/lcrm01/k4r_minigrid_source.py --output "$RUNNER_TEMP/k4r/process-a.json" > "$RUNNER_TEMP/k4r/process-a.log" 2>&1
a=$?
python -B research/lcrm01/k4r_minigrid_source.py --output "$RUNNER_TEMP/k4r/process-b.json" > "$RUNNER_TEMP/k4r/process-b.log" 2>&1
b=$?
set -e
echo "K4R_PROCESS_A_EXIT=$a K4R_PROCESS_B_EXIT=$b"
cat "$RUNNER_TEMP/k4r/process-a.log" "$RUNNER_TEMP/k4r/process-b.log"
test "$a" -eq 0 && test "$b" -eq 0
python -B research/lcrm01/k4r_compare.py --first "$RUNNER_TEMP/k4r/process-a.json" --second "$RUNNER_TEMP/k4r/process-b.json" --output "$RUNNER_TEMP/k4r/comparison.json"
test -z "$(git -C "$RUNNER_TEMP/k4r/Minigrid" status --porcelain --untracked-files=no)"
python -B - <<'PY'
import json,os
from pathlib import Path
root=Path(os.environ["RUNNER_TEMP"])/"k4r"
a=json.loads((root/"process-a.json").read_text())
b=json.loads((root/"process-b.json").read_text())
c=json.loads((root/"comparison.json").read_text())
assert a["FIT_source_episodes"]==b["FIT_source_episodes"]==48
assert (a["CHECK_episode_evaluations"],a["DEV_episode_evaluations"]) in ((0,0),(40,80))
assert a["original_K4Q_no_go_preserved"] and b["original_K4Q_no_go_preserved"]
assert not a["scientific_first_use"] and not b["scientific_first_use"]
assert not a["scientific_accepted"] and not b["scientific_accepted"]
assert c["exact_original_source_science_agreement"] is True
print("K4R_SCIENTIFIC_CUSTODY=PASS")
print("K4R_BOUNDED_SOURCE_VERDICT="+c["result"])
PY
