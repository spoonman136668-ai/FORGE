"""Original R8 source-fault reproduction and deterministic bounded proposal tests.

The Go test uses a synthetic public-environment and learner stub ONLY to prove
the RunEpisode source-custody boundary. It does not train/score the native R8
learner or invoke the original-world adapter. Real source qualification and
owner admission remain separate.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from f139.nci04_model_proposal import validate
from f139.nci04_wingless_r8_source_producer import (
    ANCHOR, BEFORE_SHA256, BLOB, LANE, MECHANISM, PATH, PARENT, REPLACEMENT,
    R8SourceDenied, git_blob, mechanism_sha256, propose,
)

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "wingless_r8_training_f8d711.go"
HISTORY = "e" * 64

STUB_R1 = """package r1

type PublicGrid struct { Direction int }
"""

STUB_TEST = """package outcome

import (
    "errors"
    "strings"
    "testing"
    r1 "github.com/spoonman136668-ai/Wingless/research/native/itd02/r1"
)

type fakePolicy struct {
    Armed bool
    EpisodeSteps uint32
    LiveSeen uint64
}
func (p *fakePolicy) Healthy() bool { return true }

type fakeRewards struct {
    Closed bool
    NextID uint64
}
func (r *fakeRewards) Valid() bool { return true }

type Selected struct {
    Policy *fakePolicy
    Rewards *fakeRewards
}
func (s *Selected) ChooseRewardExplore(before r1.PublicGrid, _ uint32) (int,error) {
    if before.Direction == 9 { return 0, errors.New("INVALID_PUBLIC_OBSERVATION") }
    return 0,nil
}
func (s *Selected) BeginEpisode() error { return nil }
func (s *Selected) Feedback(before r1.PublicGrid, action int, after r1.PublicGrid, event Event) error {
    return nil
}
func (s *Selected) SnapshotSelected() ([]byte,error) { return []byte{1},nil }

type Event struct {
    ID uint64
    Action int
    Reward float64
    Terminal bool
    Truncated bool
}
type faultyPublic struct { resets, steps int }
func (f *faultyPublic) ResetPublic() (r1.PublicGrid,error) {
    f.resets++
    return r1.PublicGrid{Direction: 9},nil
}
func (f *faultyPublic) StepPublic(_ int) (PublicConsequence,error) {
    f.steps++
    return PublicConsequence{},nil
}
func TestNativePostResetInvalidChoiceNeverReplaysReset(t *testing.T) {
    f:=&faultyPublic{}
    s:=&TrainingSession{
        Learner:&Selected{Policy:&fakePolicy{},Rewards:&fakeRewards{NextID:1}},
        MinimumSelectedSamples:2,MaximumEpisodeSteps:1,
    }
    _,_,err:=s.RunEpisode(f)
    if err==nil||!strings.Contains(err.Error(),"INVALID_PUBLIC_OBSERVATION") {
        t.Fatalf("expected first selection failure: %v",err)
    }
    _,_,err=s.RunEpisode(f)
    if err==nil||!strings.Contains(err.Error(),"SOURCE_CUSTODY_UNCONFIRMED") {
        t.Fatalf("SOURCE_RESET_REPLAY second call not refused: %v",err)
    }
    if f.resets!=1||f.steps!=0 {
        t.Fatalf("SOURCE_RESET_REPLAY reset=%d step=%d",f.resets,f.steps)
    }
}
"""


def build(*, original=None, **extra):
    before = FIXTURE.read_bytes() if original is None else original
    args = {
        "target_commit": PARENT, "path": PATH, "original_bytes": before,
        "authenticated_git_blob": BLOB, "history_sha256": HISTORY,
        "consumed_after_sha256": set(),
        "consumed_mechanism_sha256": set(),
    }
    args.update(extra)
    return propose(**args)


def go_test(source: bytes) -> subprocess.CompletedProcess:
    go = shutil.which("go")
    if not go:
        raise unittest.SkipTest("WINGLESS_R8_GO_COMPILER_NOT_AVAILABLE")
    with tempfile.TemporaryDirectory(prefix="f139-r8-source-reset-") as root:
        parent = Path(root)
        folder = parent / "research" / "native" / "itd02"
        (folder / "r1").mkdir(parents=True)
        (folder / "outcome").mkdir()
        (parent / "go.mod").write_text(
            "module github.com/spoonman136668-ai/Wingless\n\ngo 1.23\n",
            encoding="utf-8")
        (folder / "r1" / "grid.go").write_text(STUB_R1, encoding="utf-8")
        (folder / "outcome" / "training_session.go").write_bytes(source)
        (folder / "outcome" / "training_session_test.go").write_text(
            STUB_TEST, encoding="utf-8")
        env = dict(os.environ)
        env.update({"GOTOOLCHAIN": "local", "GOPROXY": "off",
                    "GOSUMDB": "off", "GO111MODULE": "on"})
        return subprocess.run(
            [go, "test", "-count=1", "-v", "./research/native/itd02/outcome"],
            cwd=parent, env=env, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, text=True, check=False, timeout=120,
        )


class R8ModelFreeProposalTests(unittest.TestCase):
    def test_authenticated_original_source(self):
        data = FIXTURE.read_bytes()
        self.assertEqual(len(data), 6312)
        self.assertEqual(git_blob(data), BLOB)
        self.assertEqual(hashlib.sha256(data).hexdigest(), BEFORE_SHA256)

    def test_deterministic_one_anchor_only(self):
        result = build()
        self.assertEqual(result, build())
        before = FIXTURE.read_bytes()
        self.assertEqual(before.count(ANCHOR.encode()), 1)
        self.assertEqual(result["source"], before.replace(
            ANCHOR.encode(), REPLACEMENT.encode(), 1))
        self.assertEqual(result["source"].count(
            b"s.quarantined = true"), before.count(b"s.quarantined = true") + 1)

    def test_original_f139_model_proposal_accepts_data(self):
        result = build()
        parsed = json.loads(result["raw_response"].decode("ascii"))
        self.assertEqual(parsed["path"], PATH)
        self.assertEqual(parsed["target_commit"], PARENT)
        self.assertEqual(parsed["lane"], LANE)
        checked = validate(
            result["raw_response"], lane=LANE,
            target_commit=PARENT, path=PATH,
            before=FIXTURE.read_bytes(), before_sha256=BEFORE_SHA256,
            history_sha256=HISTORY, consumed_candidates=set(),
            consumed_after_hashes=set())
        self.assertEqual(checked["record"]["candidate_identity"],
                         result["candidate_identity"])

    def test_no_runtime_or_science_authority(self):
        result = build()
        for field in (
            "original_source_reviewed", "original_owner_authenticated",
            "owner_publication_authorized", "worker_dispatched",
            "scientific_first_use", "new_controller", "new_scheduler",
        ):
            self.assertIs(result[field], False)
        self.assertEqual(result["paid_model_calls"], 0)
        self.assertEqual(result["mechanism_sha256"], mechanism_sha256())
        self.assertEqual(MECHANISM,
                         "r8-choice-error-after-source-reset-quarantine-v1")

    def test_consumed_candidate_never_replays(self):
        after = build()["source_after_sha256"]
        with self.assertRaisesRegex(R8SourceDenied, "AFTER_SOURCE_CONSUMED"):
            build(consumed_after_sha256={after})

    def test_consumed_mechanism_never_replays(self):
        with self.assertRaisesRegex(R8SourceDenied, "MECHANISM_CONSUMED"):
            build(consumed_mechanism_sha256={mechanism_sha256()})

    def test_parent_and_path_frozen(self):
        for opts in ({"target_commit": "0" * 40},
                     {"path": "research/jepa/stream.go"},
                     {"path": "cmd/wingless/local.go"}):
            with self.subTest(opts=opts):
                with self.assertRaisesRegex(R8SourceDenied, "TARGET_SCOPE"):
                    build(**opts)

    def test_source_identity_drift_denied(self):
        for opts in ({"authenticated_git_blob": "1" * 40},
                     {"original_bytes": FIXTURE.read_bytes() + b"\n"}):
            with self.subTest(opts=opts):
                with self.assertRaisesRegex(R8SourceDenied, "SOURCE_HISTORY_OR_AUTHORITY"):
                    build(**opts)

    def test_history_and_first_use_denied(self):
        for opts in ({"history_sha256": "0"},
                     {"consumed_after_sha256": {"bogus"}},
                     {"consumed_mechanism_sha256": {"bad"}},
                     {"scientific_first_use": True}):
            with self.subTest(opts=opts):
                with self.assertRaisesRegex(R8SourceDenied, "SOURCE_HISTORY_OR_AUTHORITY"):
                    build(**opts)

    def test_injected_operator_not_supported(self):
        with self.assertRaises(TypeError):
            build(operator_name="user-provided-source")

    def test_actual_go_negative_control_and_proposed_boundary(self):
        old = go_test(FIXTURE.read_bytes())
        self.assertNotEqual(old.returncode, 0, old.stdout[-10000:])
        self.assertIn("SOURCE_RESET_REPLAY", old.stdout)
        new = go_test(build()["source"])
        self.assertEqual(new.returncode, 0, new.stdout[-10000:])
        self.assertIn("--- PASS: TestNativePostResetInvalidChoiceNeverReplaysReset",
                      new.stdout)


if __name__ == "__main__":
    unittest.main()
