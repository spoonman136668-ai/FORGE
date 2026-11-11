"""F139 original-response compatibility, no owner/worker/PR side effects."""
from __future__ import annotations

import json
from pathlib import Path
import unittest

from f139.nci04_native_contract import canonical, digest
from f139.nci04_wingless_original_owner_adapter import (
    FROZEN_PARENT_BLOB, WinglessOwnerAdapterDenied, prepare_original_response,
)
from f139.nci04_wingless_source_producer import PARENT, PATH
from f139.nci04_model_proposal import validate

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "wingless_fastslow_9087de.go"


def original_owner_data(*, source=None):
    original = FIXTURE.read_bytes() if source is None else source
    history = "e" * 64
    request = {
        "schema": "forge.f139.model-request.v1",
        "lane": "Wingless", "target_commit": PARENT,
        "path": PATH, "controller_source_sha": "d" * 40,
        "target_tree_sha": "a" * 40,
        "before_sha256": digest(original),
        "history_sha256": history,
        "source": original.decode("utf-8", "strict"),
        "scientific_first_use": False,
        "model_execution_authorized": False,
        "publication_authorized": False,
    }
    session = {
        "schema": "forge.f139.owner-model-session.v1",
        "owner_head_seq": 74, "owner_head_sha256": "b" * 64,
        "source_sha": "d" * 40, "lane": "Wingless",
        "target_commit": PARENT, "target_tree_sha": "a" * 40,
        "path": PATH, "before_sha256": digest(original),
        "history_sha256": history,
        "request_sha256": digest(canonical(request)),
        "scientific_first_use": False, "publication_authorized": False,
    }
    return {
        "request": request, "session": session, "before": original,
        "consumed_candidates": set(), "consumed_after_hashes": set(),
    }


def build(prepared=None, **kwargs):
    return prepare_original_response(
        prepared=original_owner_data() if prepared is None else prepared,
        historical_model_after=kwargs.pop("historical_model_after", set()),
        original_git_blob_sha=kwargs.pop(
            "original_git_blob_sha", FROZEN_PARENT_BLOB),
        **kwargs)


class WinglessOwnerAdapterTests(unittest.TestCase):
    def test_exact_source_original_model_schema_parity(self):
        result = build()
        data = original_owner_data()
        validated = validate(
            result["raw_response"], lane="Wingless",
            target_commit=PARENT, path=PATH, before=data["before"],
            before_sha256=data["session"]["before_sha256"],
            history_sha256=data["session"]["history_sha256"],
            consumed_candidates=set(), consumed_after_hashes=set())
        self.assertEqual(validated["record"]["candidate_identity"],
                         result["candidate_identity"])
        self.assertEqual(validated["record"]["after_sha256"],
                         result["source_after_sha256"])

    def test_reproducible_stable_identity(self):
        self.assertEqual(build(), build())

    def test_response_discloses_development_not_authority(self):
        result = build()
        for name in ("original_owner_authenticated", "original_source_atlas_qualified",
                     "publication_authorized", "worker_dispatched",
                     "scientific_first_use"):
            self.assertIs(result[name], False)
        self.assertEqual(result["paid_api_calls"], 0)
        self.assertEqual(result["source_pr"], 389)
        payload = json.loads(result["raw_response"].decode("ascii"))
        self.assertEqual(payload["lane"], "Wingless")
        self.assertEqual(payload["path"], PATH)

    def test_exact_response_uses_only_pinned_project_source(self):
        payload = json.loads(build()["raw_response"].decode("ascii"))
        self.assertEqual(payload["target_commit"], PARENT)
        self.assertIn("math.Max(disagreement0, disagreement1) < 0.10",
                      payload["candidate_source"])

    def test_already_attempted_model_output_is_denied(self):
        after = build()["source_after_sha256"]
        with self.assertRaisesRegex(Exception, "CANDIDATE_ALREADY_CONSUMED"):
            build(historical_model_after={after})

    def test_original_native_consumed_output_is_denied(self):
        after = build()["source_after_sha256"]
        p = original_owner_data()
        p["consumed_after_hashes"].add(after)
        with self.assertRaisesRegex(Exception, "CANDIDATE_ALREADY_CONSUMED"):
            build(prepared=p)

    def test_consumed_candidate_original_validator_denies(self):
        p = original_owner_data()
        p["consumed_candidates"].add(build()["candidate_identity"])
        with self.assertRaisesRegex(Exception, "PREVIOUSLY_CONSUMED_NO_REPLAY"):
            build(prepared=p)

    def test_bad_original_blob_denied(self):
        with self.assertRaisesRegex(WinglessOwnerAdapterDenied, "FROZEN_GIT_BLOB_DRIFT"):
            build(original_git_blob_sha="f" * 40)

    def test_mutated_source_even_with_rebound_request_denied(self):
        p = original_owner_data(source=FIXTURE.read_bytes() + b"\n")
        with self.assertRaisesRegex(WinglessOwnerAdapterDenied, "FROZEN_GIT_BLOB_DRIFT"):
            build(prepared=p)

    def test_bad_original_owner_source_sha_denied(self):
        p = original_owner_data()
        p["session"]["source_sha"] = "0" * 40
        with self.assertRaisesRegex(WinglessOwnerAdapterDenied, "REQUEST_SOURCE_OR_HISTORY_DRIFT"):
            build(prepared=p)

    def test_original_history_mismatch_denied(self):
        p = original_owner_data()
        p["session"]["history_sha256"] = "c" * 64
        with self.assertRaisesRegex(WinglessOwnerAdapterDenied, "REQUEST_SOURCE_OR_HISTORY_DRIFT"):
            build(prepared=p)

    def test_false_first_use_or_publication_denied(self):
        for field in ("scientific_first_use", "publication_authorized"):
            p = original_owner_data()
            p["session"][field] = True
            with self.subTest(field=field):
                with self.assertRaisesRegex(WinglessOwnerAdapterDenied,
                                            "ORIGINAL_SESSION_BOUNDARY"):
                    build(prepared=p)

    def test_bad_owner_seq_denied(self):
        p = original_owner_data()
        p["session"]["owner_head_seq"] = 0
        with self.assertRaisesRegex(WinglessOwnerAdapterDenied, "ORIGINAL_SESSION_BOUNDARY"):
            build(prepared=p)

    def test_bad_parent_denied(self):
        p = original_owner_data()
        p["session"]["target_commit"] = "0" * 40
        with self.assertRaisesRegex(WinglessOwnerAdapterDenied, "ORIGINAL_SESSION_BOUNDARY"):
            build(prepared=p)

    def test_unknown_fields_denied(self):
        p = original_owner_data()
        p["session"]["root_permission"] = "allow"
        with self.assertRaisesRegex(WinglessOwnerAdapterDenied, "ORIGINAL_SESSION_BOUNDARY"):
            build(prepared=p)


if __name__ == "__main__":
    unittest.main()
