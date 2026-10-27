"""Proposal data cannot change owner scope or replay retained source."""
import json
import unittest
from unittest.mock import patch

from f139.nci04_model_proposal import ProposalDenied, SCHEMA, build_request, validate
from f139.nci04_native_contract import digest
from f139.nci04_proposal_compiler import prepare_proposal
from f139 import nci04_research_steering as steering
from f139.test_nci04_research_steering import SteeringProvider


class ModelProposalTests(unittest.TestCase):
    def setUp(self):
        self.before = b"class Cell:\n    pass\n"
        self.args = dict(lane="Yggdrasil", target_commit="a" * 40,
                         path="yggdrasil/cell.py", before=self.before,
                         before_sha256=digest(self.before), history_sha256="b" * 64,
                         consumed_candidates=set(), consumed_after_hashes=set())
        self.doc = {"schema": SCHEMA, "lane": "Yggdrasil",
                    "target_commit": "a" * 40, "path": "yggdrasil/cell.py",
                    "history_sha256": "b" * 64,
                    "question": "Does local evidence improve action choice?",
                    "hypothesis": "Local counts improve decisions.",
                    "control": "Compare against a matched random-action baseline.",
                    "candidate_source": "class Cell:\n    count = 1\n"}

    def call(self, doc=None, **updates):
        args = dict(self.args, **updates)
        return validate(json.dumps(doc if doc is not None else self.doc).encode(), **args)

    def test_valid_response_is_data_only_and_deterministic(self):
        first = self.call()
        self.assertEqual(first, self.call())
        self.assertFalse(first["record"]["scientific_first_use"])
        self.assertFalse(first["record"]["publication_authorized"])
        self.assertEqual(first["record"]["after_sha256"], digest(first["candidate_source"]))

    def test_target_history_and_authority_are_not_model_controlled(self):
        for field, value in [("target_commit", "c" * 40), ("path", "scripts/other.py"),
                             ("history_sha256", "c" * 64), ("scientific_first_use", True)]:
            doc = dict(self.doc, **{field: value})
            with self.subTest(field=field), self.assertRaises(ProposalDenied):
                self.call(doc)

    def test_rejects_replayed_candidate_and_source_across_parents(self):
        result = self.call()
        with self.assertRaisesRegex(ProposalDenied, "PREVIOUSLY_CONSUMED"):
            self.call(consumed_candidates={result["record"]["candidate_identity"]})
        with self.assertRaisesRegex(ProposalDenied, "PREVIOUSLY_CONSUMED"):
            self.call(consumed_after_hashes={result["record"]["after_sha256"]})

    def test_validated_bytes_fit_existing_non_authorizing_intake_contract(self):
        result = self.call()
        proposal = prepare_proposal(
            controller_source_sha="c" * 40, lane=self.args["lane"],
            target_commit=self.args["target_commit"], target_tree_sha="d" * 40,
            path=self.args["path"], before=self.before, after=result["candidate_source"],
            dependency_sha256="1" * 64, qualification_harness_sha256="2" * 64,
            training_config_sha256="3" * 64, suite_identity_sha256="4" * 64,
            toolchain_identity="python3.11.11")
        self.assertTrue(proposal["owner_issue_required"])
        self.assertFalse(proposal["eligible"])
        self.assertFalse(proposal["dispatch_authorized"])
        self.assertFalse(proposal["scientific_first_use"])

    def test_requires_matching_original_bytes_and_valid_source(self):
        with self.assertRaisesRegex(ProposalDenied, "SOURCE_OR_HISTORY_INVALID"):
            self.call(before_sha256="c" * 64)
        with self.assertRaisesRegex(ProposalDenied, "SOURCE_INVALID"):
            self.call(dict(self.doc, candidate_source="def bad(:\n"))
        with self.assertRaisesRegex(ProposalDenied, "SOURCE_SIZE_OR_CHANGE_INVALID"):
            self.call(dict(self.doc, candidate_source=self.before.decode()))

    def test_rejects_duplicate_json_keys_and_paths_outside_allowlist(self):
        raw = json.dumps(self.doc).encode().replace(b'"lane": "Yggdrasil"',
                 b'"lane": "Yggdrasil", "lane": "Yggdrasil"')
        with self.assertRaisesRegex(ProposalDenied, "DUPLICATE_JSON_KEY"):
            validate(raw, **self.args)
        with self.assertRaisesRegex(ProposalDenied, "TARGET_INVALID"):
            self.call(path="scripts/../private.py")

    def test_request_uses_pinned_steering_and_retains_negative_history(self):
        provider = SteeringProvider()
        history = [{"candidate_identity": "f" * 64, "outcome": "QUARANTINED",
                    "summary": "Earlier candidate failed qualification."}]
        with patch.object(steering, "DOCUMENTS", provider.documents):
            request = build_request(provider.get, controller_source_sha="c" * 40,
                                    lane=self.args["lane"], target_tree_sha="d" * 40,
                                    target_commit=self.args["target_commit"],
                                    path=self.args["path"], before=self.before,
                                    before_sha256=self.args["before_sha256"],
                                    history_sha256=self.args["history_sha256"],
                                    history=history)
        self.assertEqual(request["steering_source_commit"], steering.MERGED_STEERING_COMMIT)
        self.assertEqual(len(request["steering_documents"]), 4)
        self.assertEqual(request["history"][0]["outcome"], "QUARANTINED")
        history[0]["outcome"] = "VERIFIED"
        self.assertEqual(request["history"][0]["outcome"], "QUARANTINED")
        self.assertFalse(request["model_execution_authorized"])
        self.assertFalse(request["publication_authorized"])
        self.assertFalse(request["scientific_first_use"])

    def test_request_rejects_tampered_steering_and_duplicate_history(self):
        provider = SteeringProvider()
        args = dict(controller_source_sha="c" * 40, target_tree_sha="d" * 40,
                    lane=self.args["lane"], target_commit=self.args["target_commit"],
                    path=self.args["path"], before=self.before,
                    before_sha256=self.args["before_sha256"],
                    history_sha256=self.args["history_sha256"])
        row = {"candidate_identity": "f" * 64, "outcome": "NEGATIVE", "summary": "Retain"}
        with patch.object(steering, "DOCUMENTS", provider.documents):
            with self.assertRaisesRegex(ProposalDenied, "REQUEST_HISTORY_INVALID"):
                build_request(provider.get, history=[row, row], **args)
            with self.assertRaisesRegex(ProposalDenied, "REQUEST_SOURCE_OR_HISTORY_INVALID"):
                build_request(provider.get, history=[row], **dict(args, target_tree_sha="bad"))
            def tampered(route):
                value = provider.get(route)
                if "CORE-NATIVE-INTELLIGENCE.md" in route:
                    value = dict(value, sha="0" * 40)
                return value
            with self.assertRaises(steering.SteeringDenied):
                build_request(tampered, history=[row], **args)


if __name__ == "__main__":
    unittest.main()
