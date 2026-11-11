"""Authenticate a frozen Wingless Go research source and compile generated change.

No Git or network at test time, no original-owner admission or scientific data.
Requires Go to prove native compile; otherwise reports an explicit Go-tool skip.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from f139.nci04_wingless_source_producer import LANE, PARENT, PATH, propose

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "wingless_fastslow_9087de.go"
ORIGINAL_GIT_BLOB = "a33a6b7b901d424b4d40721d920d5fbf199e2f9b"
GO_NATIVE_TEST = r"""package cognition

import "testing"

func TestNoEvidenceAbstains(t *testing.T) {
    state := &FastSlowState{}
    _, ok, err := state.ChooseDisagreementProbe(0)
    if err != nil || ok { t.Fatalf("expected abstention on no evidence: ok=%v err=%v", ok, err) }
}
func TestLowEvidenceFloorAbstains(t *testing.T) {
    state := &FastSlowState{}
    state.Fast.Weights[0] = 0.2
    state.Fast.Weights[1] = 0.1
    _, ok, err := state.ChooseDisagreementProbe(0)
    if err != nil || ok { t.Fatalf("expected weak disagreement abstention: ok=%v err=%v", ok, err) }
}
func TestHighEvidenceSelects(t *testing.T) {
    state := &FastSlowState{}
    state.Fast.Weights[0] = 1
    state.Fast.Weights[1] = 3
    action, ok, err := state.ChooseDisagreementProbe(0)
    if err != nil || !ok || action != 1 {
        t.Fatalf("expected action 1 on high disagreement: action=%d ok=%v err=%v", action, ok, err)
    }
}
func TestOriginalLearningAndColdRestoreStillWork(t *testing.T) {
    state := &FastSlowState{}
    if err := state.Observe(1, 1, 1, 0.5); err != nil { t.Fatal(err) }
    data, err := state.Snapshot()
    if err != nil { t.Fatal(err) }
    var cold FastSlowState
    if err := cold.Restore(data); err != nil { t.Fatal(err) }
    if cold.Fast.Updates != 1 || cold.Slow.Updates != 1 { t.Fatal("cold state lost updates") }
    if _, err := cold.Predict(1, 1); err != nil { t.Fatal(err) }
}
"""


def sha1_git_blob(data: bytes) -> str:
    return hashlib.sha1(
        b"blob " + str(len(data)).encode("ascii") + b"\0" + data
    ).hexdigest()


def generated_source() -> bytes:
    original = FIXTURE.read_bytes()
    return propose(
        lane=LANE, parent_commit=PARENT, path=PATH,
        before_bytes=original, verified_git_blob_sha=ORIGINAL_GIT_BLOB,
        pinned_before_sha256=hashlib.sha256(original).hexdigest(),
        owner_history_sha256=hashlib.sha256(b"synthetic-ledger-fixture-only").hexdigest(),
        consumed_mechanisms=set(), consumed_source_sha256=set(),
    )["source"]


class FrozenWinglessGoIntegration(unittest.TestCase):
    def test_original_is_exact_git_blob(self):
        source = FIXTURE.read_bytes()
        self.assertEqual(sha1_git_blob(source), ORIGINAL_GIT_BLOB)
        self.assertEqual(len(source), 6152)
        self.assertIn(b"package cognition\n", source)

    def test_generated_replacement_is_single_anchor_only(self):
        original = FIXTURE.read_bytes()
        generated = generated_source()
        self.assertIn(b"math.Max(disagreement0, disagreement1) < 0.10", generated)
        self.assertEqual(generated.count(b"math.Max(disagreement0, disagreement1) < 0.10"), 1)
        self.assertEqual(
            generated.replace(
                b" // Reject low-evidence interventions; measure lost information gain against\n"
                b" // the source-identical always-probe and random-cost controls.\n"
                b" if math.Max(disagreement0, disagreement1) < 0.10 { return 0, false, nil }\n",
                b"",
                1,
            ), original,
        )

    def test_generated_go_builds_and_exercises_real_actions(self):
        # G137's original Windows Python regression runs two sharded workers
        # under a strict process-tree Job Object. Do not launch a cold native
        # Go compiler INSIDE that historical Python test envelope. The
        # independent unsharded F139 source jobs execute this same test on
        # both Linux and Windows. Only this new native check is skipped in
        # G137; all previously qualified original cases remain unchanged.
        if os.environ.get("FORGE_G137_GO"):
            self.skipTest("WINGLESS_GO_COMPILER_QUALIFIED_IN_UNSHARDED_SOURCE_CI")
        go = shutil.which("go")
        if not go:
            self.skipTest("GO_NATIVE_COMPILER_NOT_AVAILABLE_UNVERIFIED")
        original = FIXTURE.read_bytes()
        self.assertEqual(sha1_git_blob(original), ORIGINAL_GIT_BLOB)
        with tempfile.TemporaryDirectory(prefix="f139-wingless-native-") as directory:
            root = Path(directory)
            (root / "continual.go").write_bytes(generated_source())
            (root / "continual_test.go").write_text(GO_NATIVE_TEST, encoding="utf-8")
            env = dict(os.environ)
            env.update({"GO111MODULE": "off", "GOTOOLCHAIN": "local",
                        "GOPROXY": "off", "GOSUMDB": "off"})
            completed = subprocess.run(
                [go, "test", "-count=1", "-v", "continual.go", "continual_test.go"],
                cwd=root, env=env, text=True, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, timeout=120, check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stdout[-10000:])
            self.assertEqual(completed.stdout.count("--- PASS:"), 4)


if __name__ == "__main__":
    unittest.main()
