#!/usr/bin/env bash
# K4T-F6: original native cost frontier, independent FIT six-field conventional comparator.
set -euo pipefail
cd "$GITHUB_WORKSPACE"
test "$(git rev-parse '0c4bf4ba9ea4610a2c4f954d3eabea98b2343cd5^')" = 'a1dc7bf282fdb9354941b1a7ad05f37941791cb3'
git merge-base --is-ancestor 0c4bf4ba9ea4610a2c4f954d3eabea98b2343cd5 HEAD
test "$(git hash-object research/lcrm01/k4y_frozen_learned_affordance.json)" = 'c34ac2b73e07c0117ff0bea863addd358749e9cb'
test "$(git hash-object research/lcrm01/k4t_f6_frozen_r7_physical.json)" = 'c733d053a10bb4b12d8de87ca846a8e006cbd881'
test "$(git hash-object research/lcrm01/k4u_native_minigrid.py)" = 'd0e0a4ac9396a05f9fb024aa09cd64407769459b'
test "$(git hash-object research/lcrm01/k4y_native_affordance.py)" = '251ca00f7334809ef9afe815992272d0e3a68379'
test "$(git hash-object research/lcrm01/k4x_frozen_curriculum_intervention.json)" = '664f0c92070ed5bedc70ba934edce9adaf9cdb4f'
echo 'K4T_F6_FROZEN_PREREG_BEFORE_ORIGINAL_SOURCE_USE=PASS'
python -B - <<'PY'
import ast,pathlib
for x in ("k4t_f6_original_r7_physical.py","k4t_f4_sixfield_conventional.py","k4t_f6_compare.py","k4y_native_affordance.py","k4y_compare.py","k4y_fetch_sources.py"):
 ast.parse((pathlib.Path("research/lcrm01")/x).read_text())
print("K4T_F6_SOURCE_AST=PASS")
PY
export PYTHONPATH="$GITHUB_WORKSPACE/research/lcrm01"
python -B -m unittest discover -s research/lcrm01 -p 'test_k4t_f6_sourceonly.py' -v
python -B -m unittest discover -s research/lcrm01 -p 'test_k4t_wingless_wire.py' -v
mkdir -p "$RUNNER_TEMP/k4tf6/minigrid" "$RUNNER_TEMP/k4tf6/go/research/native/itd02/r1" "$RUNNER_TEMP/k4tf6/go/research/native/itd02/r2" "$RUNNER_TEMP/k4tf6/go/research/native/itd02/r3" "$RUNNER_TEMP/k4tf6/go/research/native/itd02/r4" "$RUNNER_TEMP/k4tf6/go/research/native/itd02/r5" "$RUNNER_TEMP/k4tf6/go/research/native/itd02/r6" "$RUNNER_TEMP/k4tf6/go/research/native/itd02/r7" "$RUNNER_TEMP/k4tf6/yggroot/research/native/itd02/r1" "$RUNNER_TEMP/k4tf6/yggroot/research/native/itd02/r2"
python -m pip install 'pip==24.0' 'setuptools==69.5.1' 'wheel==0.43.0'
python -m pip install 'numpy==1.26.4' 'gymnasium==1.1.1' 'pygame-ce==2.5.3'
git init -q "$RUNNER_TEMP/k4tf6/minigrid"
git -C "$RUNNER_TEMP/k4tf6/minigrid" remote add origin https://github.com/Farama-Foundation/Minigrid.git
git -C "$RUNNER_TEMP/k4tf6/minigrid" fetch --no-tags --depth 1 origin 7f5853792ea7f04f75614661006d87fcf949f26d
git -C "$RUNNER_TEMP/k4tf6/minigrid" checkout --detach -q 7f5853792ea7f04f75614661006d87fcf949f26d
test "$(git -C "$RUNNER_TEMP/k4tf6/minigrid" hash-object minigrid/envs/empty.py)" = '8810bb0fa156d18475022edd8859b135ef745a5f'
test "$(git -C "$RUNNER_TEMP/k4tf6/minigrid" hash-object minigrid/envs/fourrooms.py)" = 'd79f007e00f95f48284da66d760872483c02fab2'
test "$(git -C "$RUNNER_TEMP/k4tf6/minigrid" hash-object minigrid/wrappers.py)" = '1eb2da8fb612653c97f443ff6c7492ed3f1aaa80'
test "$(git -C "$RUNNER_TEMP/k4tf6/minigrid" hash-object minigrid/minigrid_env.py)" = 'eb29e9a902de0715ab77ec981a2113576d7664fa'
python -m pip install --no-deps -e "$RUNNER_TEMP/k4tf6/minigrid"
python -B research/lcrm01/k4y_fetch_sources.py \
 --wingless-R1 "$RUNNER_TEMP/k4tf6/go/research/native/itd02/r1/policy.go" \
 --wingless-R2 "$RUNNER_TEMP/k4tf6/go/research/native/itd02/r2/affordance.go" \
 --yggdrasil-R1 "$RUNNER_TEMP/k4tf6/yggroot/research/native/itd02/r1/native_policy.py" \
 --yggdrasil-R2 "$RUNNER_TEMP/k4tf6/yggroot/research/native/itd02/r2/affordance_cells.py"
cp "$RUNNER_TEMP/k4tf6/yggroot/research/native/itd02/r1/native_policy.py" "$RUNNER_TEMP/k4tf6/yggroot/native_policy.py"
git init -q "$RUNNER_TEMP/k4tf6/original-r3"
git -C "$RUNNER_TEMP/k4tf6/original-r3" remote add origin https://github.com/spoonman136668-ai/Wingless.git
git -C "$RUNNER_TEMP/k4tf6/original-r3" fetch --no-tags --depth 1 origin 3b11363b93e61311a8e96de2546b1a7f7f62d5db
git -C "$RUNNER_TEMP/k4tf6/original-r3" checkout --detach -q 3b11363b93e61311a8e96de2546b1a7f7f62d5db
test "$(git -C "$RUNNER_TEMP/k4tf6/original-r3" hash-object research/native/itd02/r3/transitions.go)" = '3c8a60a5037e6c0f04648ae53175ed1187b5f8ac'
test "$(git -C "$RUNNER_TEMP/k4tf6/original-r3" hash-object research/native/itd02/r3/transitions_test.go)" = '0da274847ea853a2167ce6e81612073202abee34'
cp "$RUNNER_TEMP/k4tf6/original-r3/research/native/itd02/r3/transitions.go" "$RUNNER_TEMP/k4tf6/go/research/native/itd02/r3/transitions.go"
cp "$RUNNER_TEMP/k4tf6/original-r3/research/native/itd02/r3/transitions_test.go" "$RUNNER_TEMP/k4tf6/go/research/native/itd02/r3/transitions_test.go"
echo 'K4T_F6_ORIGINAL_R3_SOURCE_BLOBS_AUTHENTICATED=PASS'
git init -q "$RUNNER_TEMP/k4tf6/original-r4"
git -C "$RUNNER_TEMP/k4tf6/original-r4" remote add origin https://github.com/spoonman136668-ai/Wingless.git
git -C "$RUNNER_TEMP/k4tf6/original-r4" fetch --no-tags --depth 1 origin 1b1bea442027132df5acdf67b8353e9a5a3046f4
git -C "$RUNNER_TEMP/k4tf6/original-r4" checkout --detach -q 1b1bea442027132df5acdf67b8353e9a5a3046f4
test "$(git -C "$RUNNER_TEMP/k4tf6/original-r4" hash-object research/native/itd02/r4/frontier.go)" = '61678ff1c95966151f1b1731fef62b804504cdf8'
test "$(git -C "$RUNNER_TEMP/k4tf6/original-r4" hash-object research/native/itd02/r4/frontier_test.go)" = 'f1453a420ba163d7c69fa20e7d384dc2c85b6c7e'
cp "$RUNNER_TEMP/k4tf6/original-r4/research/native/itd02/r4/frontier.go" "$RUNNER_TEMP/k4tf6/go/research/native/itd02/r4/frontier.go"
cp "$RUNNER_TEMP/k4tf6/original-r4/research/native/itd02/r4/frontier_test.go" "$RUNNER_TEMP/k4tf6/go/research/native/itd02/r4/frontier_test.go"
echo 'K4T_F6_ORIGINAL_R4_SOURCE_BLOBS_AUTHENTICATED=PASS'
git init -q "$RUNNER_TEMP/k4tf6/original-r5"
git -C "$RUNNER_TEMP/k4tf6/original-r5" remote add origin https://github.com/spoonman136668-ai/Wingless.git
git -C "$RUNNER_TEMP/k4tf6/original-r5" fetch --no-tags --depth 1 origin 978825064dd6076058a1a38ae1a9a3d80e28d99e
git -C "$RUNNER_TEMP/k4tf6/original-r5" checkout --detach -q 978825064dd6076058a1a38ae1a9a3d80e28d99e
test "$(git -C "$RUNNER_TEMP/k4tf6/original-r5" hash-object research/native/itd02/r5/cost_frontier.go)" = '239a5f2ab6d122b10cd5c7cc9388d154929b9888'
test "$(git -C "$RUNNER_TEMP/k4tf6/original-r5" hash-object research/native/itd02/r5/cost_frontier_test.go)" = '8abce13a7498bd32001d2ece544483a996de2d9d'
cp "$RUNNER_TEMP/k4tf6/original-r5/research/native/itd02/r5/cost_frontier.go" "$RUNNER_TEMP/k4tf6/go/research/native/itd02/r5/cost_frontier.go"
cp "$RUNNER_TEMP/k4tf6/original-r5/research/native/itd02/r5/cost_frontier_test.go" "$RUNNER_TEMP/k4tf6/go/research/native/itd02/r5/cost_frontier_test.go"
echo 'K4T_F6_ORIGINAL_R5_SOURCE_AUTHENTICATED=PASS'
git init -q "$RUNNER_TEMP/k4tf6/original-r6"
git -C "$RUNNER_TEMP/k4tf6/original-r6" remote add origin https://github.com/spoonman136668-ai/Wingless.git
git -C "$RUNNER_TEMP/k4tf6/original-r6" fetch --no-tags --depth 1 origin c6850eabab1a0deafdfc71883c1e33f24c035d31
git -C "$RUNNER_TEMP/k4tf6/original-r6" checkout --detach -q c6850eabab1a0deafdfc71883c1e33f24c035d31
test "$(git -C "$RUNNER_TEMP/k4tf6/original-r6" hash-object research/native/itd02/r6/observed_edges.go)" = '08af1b25ed6e5a260ef27e6baf0310e974e71f4c'
test "$(git -C "$RUNNER_TEMP/k4tf6/original-r6" hash-object research/native/itd02/r6/observed_edges_test.go)" = '95eda8a6c28b895383378e28e45d992253872997'
cp "$RUNNER_TEMP/k4tf6/original-r6/research/native/itd02/r6/observed_edges.go" "$RUNNER_TEMP/k4tf6/go/research/native/itd02/r6/observed_edges.go"
cp "$RUNNER_TEMP/k4tf6/original-r6/research/native/itd02/r6/observed_edges_test.go" "$RUNNER_TEMP/k4tf6/go/research/native/itd02/r6/observed_edges_test.go"
echo 'K4T_F6_ORIGINAL_R6_SOURCE_AUTHENTICATED=PASS'
git init -q "$RUNNER_TEMP/k4tf6/original-r7"
git -C "$RUNNER_TEMP/k4tf6/original-r7" remote add origin https://github.com/spoonman136668-ai/Wingless.git
git -C "$RUNNER_TEMP/k4tf6/original-r7" fetch --no-tags --depth 1 origin 7980717a7b751844c154cdd35e795c21d9679464
git -C "$RUNNER_TEMP/k4tf6/original-r7" checkout --detach -q 7980717a7b751844c154cdd35e795c21d9679464
test "$(git -C "$RUNNER_TEMP/k4tf6/original-r7" hash-object research/native/itd02/r7/physical_frontier.go)" = '4dcb8d83fe40be2f31faa90dac463ccf31485945'
test "$(git -C "$RUNNER_TEMP/k4tf6/original-r7" hash-object research/native/itd02/r7/physical_frontier_test.go)" = '11c32981d71a0088e785d42e0ddd1a66a0cb8e12'
cp "$RUNNER_TEMP/k4tf6/original-r7/research/native/itd02/r7/physical_frontier.go" "$RUNNER_TEMP/k4tf6/go/research/native/itd02/r7/physical_frontier.go"
cp "$RUNNER_TEMP/k4tf6/original-r7/research/native/itd02/r7/physical_frontier_test.go" "$RUNNER_TEMP/k4tf6/go/research/native/itd02/r7/physical_frontier_test.go"
echo 'K4T_F6_ORIGINAL_R7_SOURCE_AUTHENTICATED=PASS'
printf 'module github.com/spoonman136668-ai/Wingless\n\ngo 1.25.0\n' > "$RUNNER_TEMP/k4tf6/go/go.mod"
sed 's|"k4u/wingless"|"github.com/spoonman136668-ai/Wingless/research/native/itd02/r1"|' research/lcrm01/k4u_wingless_bridge.go > "$RUNNER_TEMP/k4tf6/go/bridge_r1.go"
cp research/lcrm01/k4y_wingless_r2_bridge.go "$RUNNER_TEMP/k4tf6/go/bridge_r2.go"
cp research/lcrm01/k4t_f2_wingless_r3_bridge.go "$RUNNER_TEMP/k4tf6/go/bridge_r3.go"
cp research/lcrm01/k4t_f3_wingless_r4_bridge.go "$RUNNER_TEMP/k4tf6/go/bridge_r4.go"
cp research/lcrm01/k4t_f4_wingless_r5_bridge.go "$RUNNER_TEMP/k4tf6/go/bridge_r5.go"
cp research/lcrm01/k4t_f5_wingless_r6_bridge.go "$RUNNER_TEMP/k4tf6/go/bridge_r6.go"
cp research/lcrm01/k4t_f6_wingless_r7_bridge.go "$RUNNER_TEMP/k4tf6/go/bridge_r7.go"
(cd "$RUNNER_TEMP/k4tf6/go" && go build -trimpath -o "$RUNNER_TEMP/k4tf6/wingless-r1" bridge_r1.go)
(cd "$RUNNER_TEMP/k4tf6/go" && go build -trimpath -o "$RUNNER_TEMP/k4tf6/wingless-r2" bridge_r2.go)
(cd "$RUNNER_TEMP/k4tf6/go" && go test -count=1 ./research/native/itd02/r3)
(cd "$RUNNER_TEMP/k4tf6/go" && go vet ./research/native/itd02/r3)
(cd "$RUNNER_TEMP/k4tf6/go" && go build -trimpath -o "$RUNNER_TEMP/k4tf6/wingless-r3" bridge_r3.go)
(cd "$RUNNER_TEMP/k4tf6/go" && go test -count=1 ./research/native/itd02/r4)
(cd "$RUNNER_TEMP/k4tf6/go" && go vet ./research/native/itd02/r4)
(cd "$RUNNER_TEMP/k4tf6/go" && go build -trimpath -o "$RUNNER_TEMP/k4tf6/wingless-r4" bridge_r4.go)
(cd "$RUNNER_TEMP/k4tf6/go" && go test -count=1 ./research/native/itd02/r5)
(cd "$RUNNER_TEMP/k4tf6/go" && go vet ./research/native/itd02/r5)
(cd "$RUNNER_TEMP/k4tf6/go" && go build -trimpath -o "$RUNNER_TEMP/k4tf6/wingless-r5" bridge_r5.go)
(cd "$RUNNER_TEMP/k4tf6/go" && go test -count=1 ./research/native/itd02/r6)
(cd "$RUNNER_TEMP/k4tf6/go" && go vet ./research/native/itd02/r6)
(cd "$RUNNER_TEMP/k4tf6/go" && go build -trimpath -o "$RUNNER_TEMP/k4tf6/wingless-r6" bridge_r6.go)
export PYTHONPATH="$RUNNER_TEMP/k4tf6/yggroot:$GITHUB_WORKSPACE/research/lcrm01"
set +e
python -B research/lcrm01/k4t_f6_original_r7_physical.py \
 --wingless-r1 "$RUNNER_TEMP/k4tf6/wingless-r1" \
 --wingless-r2 "$RUNNER_TEMP/k4tf6/wingless-r2" \
 --wingless-r3 "$RUNNER_TEMP/k4tf6/wingless-r3" \
 --wingless-r4 "$RUNNER_TEMP/k4tf6/wingless-r4" \
 --wingless-r5 "$RUNNER_TEMP/k4tf6/wingless-r5" \
 --wingless-r6 "$RUNNER_TEMP/k4tf6/wingless-r6" \
 --yggdrasil-source "$RUNNER_TEMP/k4tf6/yggroot" \
 --output "$RUNNER_TEMP/k4tf6/process-a.json" > "$RUNNER_TEMP/k4tf6/process-a.log" 2>&1
a=$?
python -B research/lcrm01/k4t_f6_original_r7_physical.py \
 --wingless-r1 "$RUNNER_TEMP/k4tf6/wingless-r1" \
 --wingless-r2 "$RUNNER_TEMP/k4tf6/wingless-r2" \
 --wingless-r3 "$RUNNER_TEMP/k4tf6/wingless-r3" \
 --wingless-r4 "$RUNNER_TEMP/k4tf6/wingless-r4" \
 --wingless-r5 "$RUNNER_TEMP/k4tf6/wingless-r5" \
 --wingless-r6 "$RUNNER_TEMP/k4tf6/wingless-r6" \
 --yggdrasil-source "$RUNNER_TEMP/k4tf6/yggroot" \
 --output "$RUNNER_TEMP/k4tf6/process-b.json" > "$RUNNER_TEMP/k4tf6/process-b.log" 2>&1
b=$?
set -e
echo "K4T_F6_PROCESS_A_EXIT=$a K4T_F6_PROCESS_B_EXIT=$b"
cat "$RUNNER_TEMP/k4tf6/process-a.log" "$RUNNER_TEMP/k4tf6/process-b.log"
test "$a" -eq 0 && test "$b" -eq 0
python -B research/lcrm01/k4t_f6_compare.py \
 --first "$RUNNER_TEMP/k4tf6/process-a.json" \
 --second "$RUNNER_TEMP/k4tf6/process-b.json" \
 --output "$RUNNER_TEMP/k4tf6/comparison.json"
test -z "$(git -C "$RUNNER_TEMP/k4tf6/minigrid" status --porcelain --untracked-files=no)"
export WINGLESS_R1_NATIVE_BRIDGE="$RUNNER_TEMP/k4tf6/wingless-r1"
export WINGLESS_R2_NATIVE_BRIDGE="$RUNNER_TEMP/k4tf6/wingless-r2"
python -B -m unittest discover -s research/lcrm01 -p 'test_k4t_wingless_wire.py' -v
python -B - <<'PY'
import json,os,pathlib
root=pathlib.Path(os.environ["RUNNER_TEMP"])/"k4tf6"
a=json.loads((root/"process-a.json").read_text())
b=json.loads((root/"process-b.json").read_text())
c=json.loads((root/"comparison.json").read_text())
assert a["FIT_public_experience_count"]==b["FIT_public_experience_count"]==12000
assert a["CHECK_episodes"]==b["CHECK_episodes"]==120
assert a["DEV_episodes"]==b["DEV_episodes"]==240
assert a["scientific_accepted"] is False and b["scientific_accepted"] is False
assert c["science_identical"] is True
print("K4T_F6_SOURCE_AND_SCIENCE_REPEATED=PASS")
print("K4T_F6_R6_ROUTE_DISPOSITION="+c["result"])
PY
