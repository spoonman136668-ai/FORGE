#!/usr/bin/env python3
"""Source-only adversarial checks. Fake SHA values here are NOT source evidence."""
import copy
import unittest

from l10_b8_source_preflight import (
    SCHEMA, FAMILY_KIND, ROLE, RESULT, check_manifest,
)


def proposal():
    return {
        "schema": SCHEMA,
        "family_id": "l10p-new-graph-role-composition",
        "family_kind": FAMILY_KIND,
        "generator": {
            "repository": "independent-original/formal-world",
            "commit_sha": "a" * 40,
            "blob_sha": "b" * 40,
            "path": "original/source.py",
        },
        "grammar": {
            "repository": "independent-original/formal-world",
            "commit_sha": "a" * 40,
            "blob_sha": "c" * 40,
            "path": "original/grammar.json",
        },
        "scorer": {
            "repository": "independent-audit/scorer",
            "commit_sha": "d" * 40,
            "blob_sha": "e" * 40,
            "path": "audit/semantic_oracle.py",
        },
        "custody": {
            "source_owner": "original-source-owner",
            "scorer_owner": "independent-auditor",
            "candidate_owner": "separate-candidate-team",
            "source_birth": "UNBORN",
            "owner_receipt": "NOT_PRESENT",
            "fsa_admission": "DENIED",
        },
        "information_regime": {
            "mapping_regime": "KNOWN_MAPPING",
            "public_relation_codes": ["P0", "P1", "P2"],
            "lexicon_rights": "MATCHED_PUBLIC_ONLY",
            "model_truth_fields_exposed": False,
            "scorer_source_access": "SEPARATE_OWNER_ONLY",
        },
        "data_access": {
            "role": ROLE,
            "examples_generated": 0,
            "protected_seed_exposed": False,
            "protected_bytes_exposed": False,
            "l9_data_reused": False,
        },
        "counts": {
            "prospective_examples": 0,
            "selected_models": 0,
            "protected_source_observations": 0,
        },
    }


class L10B8PreflightTests(unittest.TestCase):
    def reject(self, field, value, fragment):
        candidate = proposal()
        cursor = candidate
        for part in field[:-1]:
            cursor = cursor[part]
        cursor[field[-1]] = value
        with self.assertRaisesRegex(ValueError, fragment):
            check_manifest(candidate)

    def test_metadata_shape_is_never_scientific_admission(self):
        res = check_manifest(proposal())
        self.assertEqual(res["status"], RESULT)
        self.assertFalse(res["original_sources_authenticated"])
        self.assertFalse(res["independent_owner_receipts_authenticated"])
        self.assertFalse(res["scientific_first_use_admitted"])
        self.assertFalse(res["comparison_scored"])
        self.assertTrue(res["requires_independent_FSA_review"])
        self.assertEqual(res["prospective_examples_read"], 0)

    def test_identical_lint_digest(self):
        self.assertEqual(check_manifest(proposal()), check_manifest(copy.deepcopy(proposal())))

    def test_ban_payload_at_root(self):
        x = proposal()
        x["protected_seed"] = 720391
        with self.assertRaisesRegex(ValueError, "ROOT_FIELDS"):
            check_manifest(x)

    def test_ban_payload_nested(self):
        x = proposal()
        x["generator"]["raw_corpus"] = ["not an actual example"]
        with self.assertRaisesRegex(ValueError, "GENERATOR_FIELDS"):
            check_manifest(x)

    def test_reject_old_webnlg(self):
        self.reject(["family_id"], "l10p-webnlg-categories", "UNFAMILIAR_FAMILY_ID")

    def test_reject_old_l9(self):
        self.reject(["family_id"], "l10p-l9-reuse", "UNFAMILIAR_FAMILY_ID")

    def test_reject_wrong_kind(self):
        self.reject(["family_kind"], "external_benchmark", "FROZEN_FAMILY_KIND")

    def test_wrong_repository(self):
        self.reject(["generator", "repository"], "invalid repo", "GENERATOR_REPOSITORY")

    def test_nonimmutable_commit(self):
        self.reject(["scorer", "commit_sha"], "main", "SCORER_COMMIT_SHA")

    def test_source_path_traversal(self):
        self.reject(["generator", "path"], "../protected.json", "GENERATOR_PATH")

    def test_generator_and_scorer_same_repo(self):
        self.reject(["scorer", "repository"],
                    proposal()["generator"]["repository"], "SCORER_NOT_SEPARATE_SOURCE")

    def test_duplicate_identity(self):
        self.reject(["grammar"], proposal()["generator"], "COLLAPSED")

    def test_claimed_owner_identity_collision(self):
        self.reject(["custody", "scorer_owner"],
                    proposal()["custody"]["source_owner"], "CUSTODY_SEPARATION_CLAIM")

    def test_forbid_fabricated_owner_receipt(self):
        self.reject(["custody", "owner_receipt"], "PASS", "NO_SOURCE_BIRTH_AUTHORITY")

    def test_forbid_claimed_fsa_admission(self):
        self.reject(["custody", "fsa_admission"], "GRANTED", "NO_SOURCE_BIRTH_AUTHORITY")

    def test_prospective_birth_not_started(self):
        self.reject(["custody", "source_birth"], "GENERATED", "NO_SOURCE_BIRTH_AUTHORITY")

    def test_withheld_mapping_is_not_matched_positive(self):
        self.reject(["information_regime", "mapping_regime"],
                    "WITHHELD_MAPPING", "INFORMATION_LEAK_OR_REGIME_DRIFT")

    def test_deny_hidden_mapping(self):
        self.reject(["information_regime", "model_truth_fields_exposed"], True,
                    "INFORMATION_LEAK_OR_REGIME_DRIFT")

    def test_deny_protected_seed_exposure(self):
        self.reject(["data_access", "protected_seed_exposed"], True,
                    "PROTECTED_SOURCE_BOUNDARY")

    def test_deny_protected_generation(self):
        self.reject(["data_access", "examples_generated"], 1,
                    "PROTECTED_SOURCE_BOUNDARY")

    def test_deny_protected_role_change(self):
        self.reject(["data_access", "role"], "L10_SYNTHETIC_DEV",
                    "PROTECTED_SOURCE_BOUNDARY")

    def test_deny_reused_l9_evidence(self):
        self.reject(["data_access", "l9_data_reused"], True,
                    "PROTECTED_SOURCE_BOUNDARY")

    def test_deny_selected_model_after_protected_source(self):
        self.reject(["counts", "selected_models"], 1,
                    "PROSPECTIVE_DATA_OR_MODEL_SELECTION")

    def test_deny_fake_numeric_boolean_count(self):
        self.reject(["counts", "prospective_examples"], False,
                    "PROSPECTIVE_DATA_OR_MODEL_SELECTION")

    def test_deny_unknown_top_level_schema(self):
        self.reject(["schema"], "different-v1", "SCHEMA")


if __name__ == "__main__":
    unittest.main()
