"""F139 NCI-04 isolated contract tests: no network, shell, queue or controller writes."""
import base64
import hashlib
import json
import unittest

from nci04_native_contract import (SCHEMA, NativeContractError, parse_intent, digest)

FORGE = "a" * 40
TARGET = "b" * 40
TREE = "c" * 40
ZERO = digest(b"")
AFTER = b"package research\n\n// bounded candidate source edit\n"


def intent(lane="Wingless"):
    wing = lane == "Wingless"
    return {
        "schema": SCHEMA,
        "controller_source_sha": FORGE,
        "lane": lane,
        "target_repository": "spoonman136668-ai/Wingless" if wing else "spoonman136668-ai/Yggdrasil",
        "target_commit": TARGET,
        "target_tree_sha": TREE,
        "dependency_sha256": "d" * 64,
        "qualification_harness_sha256": "e" * 64,
        "training_config_sha256": "f" * 64,
        "toolchain_identity": "go1.25.0" if wing else "python3.11",
        "suite_identity_sha256": "1" * 64,
        "path": "cognition/native_state.go" if wing else "yggdrasil/native_state.py",
        "before_sha256": ZERO,
        "after_sha256": digest(AFTER),
        "after_base64": base64.b64encode(AFTER).decode(),
        "worker_mode": "isolated-candidate-only",
        "scientific_first_use": False,
        "paid_api_calls": 0,
        "accepted_ref_mutations": 0,
        "optimizer_policy_mutations": 0,
        "protected_holdouts_accessed": 0,
    }


def encoded(x):
    return json.dumps(x, sort_keys=True, separators=(",", ":")).encode()


class NativeContractTests(unittest.TestCase):
    def parse(self, obj, **identity):
        return parse_intent(encoded(obj), protected_main=identity.get("protected_main", FORGE),
                            target_commit=identity.get("target_commit", TARGET),
                            target_tree_sha=identity.get("target_tree_sha", TREE))

    def reject(self, obj, expected=None, **identity):
        with self.assertRaises(NativeContractError) as ctx:
            self.parse(obj, **identity)
        if expected:
            self.assertIn(expected, str(ctx.exception))

    def test_valid_one_file_native_contract(self):
        for lane in ("Wingless", "Yggdrasil"):
            with self.subTest(lane=lane):
                candidate = self.parse(intent(lane))
                self.assertEqual(candidate.materialize_bytes(b""), AFTER)
                self.assertEqual(len(candidate.qualification_key), 64)
                self.assertEqual(candidate.lane, lane)

    def test_quarantined_original_toolchain_identity_retained(self):
        # Historical issue #696 is immutable: newer source parsing must not
        # invalidate the originally authenticated negative event-chain input.
        old = intent("Yggdrasil")
        old["toolchain_identity"] = "python3.11.11"
        historic = self.parse(old)
        current = self.parse(intent("Yggdrasil"))
        self.assertNotEqual(historic.qualification_key, current.qualification_key)
        self.assertEqual(historic.lane, "Yggdrasil")
        self.assertEqual(current.lane, "Yggdrasil")

    def test_original_drift_fails_closed(self):
        with self.assertRaisesRegex(NativeContractError, "ORIGINAL_BYTES_DRIFT"):
            self.parse(intent()).materialize_bytes(b"unexpected")

    def test_identity_drift(self):
        self.reject(intent(), "CONTROLLER_IDENTITY_DRIFT", protected_main="9" * 40)
        self.reject(intent(), "TARGET_COMMIT_DRIFT", target_commit="8" * 40)
        self.reject(intent(), "TARGET_TREE_DRIFT", target_tree_sha="7" * 40)

    def test_no_cross_lane_or_arbitrary_repository(self):
        for path in (".github/workflows/bypass.go", "../research/native_state.go",
                     "cognition/../tests/bypass.go", "cognition//bypass.go",
                     "cognition\\escape.go", "cognition/bypass.py", ".git/config",
                     "cognition/a;touch-b.go", "/cognition/native.go",
                     "cognition/CON.go", "cognition/.git/native.go", "cognition/folder./native.go"):
            with self.subTest(path=path):
                bad = intent()
                bad["path"] = path
                self.reject(bad, "SOURCE_PATH_FORBIDDEN")
        bad = intent()
        bad["target_repository"] = "untrusted/project"
        self.reject(bad, "REPOSITORY_LANE_MISMATCH")

    def test_reject_authority_escalation_and_bad_types(self):
        for k, value in (("scientific_first_use", True), ("paid_api_calls", 1),
                         ("accepted_ref_mutations", 1), ("optimizer_policy_mutations", 1),
                         ("protected_holdouts_accessed", 1), ("paid_api_calls", False),
                         ("worker_mode", "shell")):
            with self.subTest(field=k):
                bad = intent()
                bad[k] = value
                self.reject(bad, "AUTHORITY_ESCALATION_REJECTED")

    def test_digest_and_cache_key_invalidation(self):
        base = self.parse(intent())
        for field in ("dependency_sha256", "training_config_sha256", "qualification_harness_sha256",
                      "suite_identity_sha256", "target_tree_sha", "target_commit"):
            bad = intent()
            bad[field] = "2" * (40 if field.endswith("_sha") or field == "target_commit" else 64)
            kwargs = {"target_commit": bad["target_commit"], "target_tree_sha": bad["target_tree_sha"]}
            altered = self.parse(bad, **kwargs)
            self.assertNotEqual(base.qualification_key, altered.qualification_key)

    def test_reject_invalid_encoding_and_content(self):
        for value in ("!!!", "", "AA==", "////", " " * 20):
            bad = intent()
            bad["after_base64"] = value
            self.reject(bad)
        bad = intent()
        bad["after_sha256"] = "0" * 64
        self.reject(bad, "CANDIDATE_DIGEST_OR_NOOP")
        bad = intent()
        bad["before_sha256"] = bad["after_sha256"]
        self.reject(bad, "CANDIDATE_DIGEST_OR_NOOP")

    def test_typed_malformed_input_and_duplicate_key_rejected(self):
        bad = intent()
        bad["lane"] = []
        self.reject(bad, "LANE_FORBIDDEN")
        repeated = encoded(intent()).decode().replace('"schema":', '"schema":"evil","schema":', 1)
        with self.assertRaisesRegex(NativeContractError, "DUPLICATE_JSON_KEY"):
            parse_intent(repeated.encode(), protected_main=FORGE,
                         target_commit=TARGET, target_tree_sha=TREE)

    def test_extra_fields_and_raw_prompt_rejected(self):
        bad = intent()
        bad["shell"] = "sudo dangerous"
        self.reject(bad, "INTENT_FIELDS_INVALID")
        bad = intent()
        bad.pop("suite_identity_sha256")
        self.reject(bad, "INTENT_FIELDS_INVALID")
        with self.assertRaises(NativeContractError):
            parse_intent(b"no json", protected_main=FORGE,
                         target_commit=TARGET, target_tree_sha=TREE)


if __name__ == "__main__":
    unittest.main()
