"""G33 no-secret synthetic owner/provider MAC contract and negative matrix."""
import copy
import hashlib
import hmac
import unittest

from f139 import nci04_v19_g33_signature_contract as g

OWNER_KEY = b"owner-unit-test-never-production-0123456789012"
LINUX_KEY = b"linux-unit-test-never-production-01234567890"
WIN_KEY = b"windows-unit-test-never-production-0123456789"
KEYS = {"ubuntu-latest": LINUX_KEY, "windows-latest": WIN_KEY}
RUN = 40999991234


def sign(binding, key, domain):
    return {"binding": binding,
            "hmac_sha256": hmac.new(key, domain + g.canonical(binding),
                                   hashlib.sha256).hexdigest()}


def g32_report():
    return {
        "schema": g.G32_SCHEMA, "source_run_id": g.DIAGNOSTIC_RUN,
        "git_authenticated_metadata_download_required": True,
        "original_artifact_ids": {
            "linux": 12900619626, "windows": 12901923435},
        "original_zip_sha256": {
            "linux": "4cd4bf9a236dff693e35173e2c4774b6a0cf6abf0cfc2d6724903ab6e21a5c19",
            "windows": "8f47dae9acc904d778aea5874795b11d92f8d1ec2feb5aee2834f43dd4d0e15e"},
        "provider_receipt_signed": False,
        "original_owner_consumed": False, "native_qualified": False,
        "full_native_worker_regression_qualified": False,
        "production_release_authorized": False, "scientific_first_use": False,
        "diagnostic": {"windows_historical_regression": "NEGATIVE_RETAINED",
                       "native_qualified": False,
                       "signed_provider_success": False},
    }


def fixture():
    g32 = g32_report()
    o = {
        "schema": g.OWNER,
        "ticket": "f139-nci04-i1200-" + g.SOURCE[:12] + "-" + "a"*8,
        "owner_source_sha": g.SOURCE, "owner_epoch": 9,
        "original_event_seq": 323, "original_event_sha256": "b"*64,
        "issue_number": 1200, "issue_id": 999990001,
        "native_intent_sha256": "a"*64, "qualification_key": "c"*64,
        "target_commit": g.TARGET_COMMIT, "target_tree": g.TARGET_TREE,
        "path": g.NATIVE_PATH, "candidate_after_sha256": "d"*64,
        "provider_run_id": RUN, "development_only": True,
        "scientific_first_use": False, "paid_model_calls": 0,
        "accepted_ref_mutations": 0}
    providers, provenance = [], {}
    for idx, os in enumerate(g.RUNNER_OSES):
        p = {
            "schema": g.PROVIDER, "ticket": o["ticket"],
            "owner_source_sha": o["owner_source_sha"],
            "owner_event_sha256": o["original_event_sha256"],
            "native_intent_sha256": o["native_intent_sha256"],
            "qualification_key": o["qualification_key"],
            "target_commit": o["target_commit"],
            "target_tree": o["target_tree"], "path": o["path"],
            "candidate_after_sha256": o["candidate_after_sha256"],
            "provider_run_id": RUN, "provider_job_id": 100001 + idx,
            "runner_os": os, "artifact_sha256": ("e" if idx == 0 else "f")*64,
            "baseline_g29_pass_count": 4, "baseline_full_pass_count": 53,
            "candidate_g29_expected_negative_count": 2,
            "candidate_applicable_test_count": 49,
            "candidate_test_module_count": 4, "candidate_compiled": True,
            "child_cpu_measured": True, "child_rss_measured": True,
            "resource_budget_enforced": True, "native_qualified": True,
            "scientific_first_use": False, "accepted_ref_mutations": 0,
            "paid_model_calls": 0}
        providers.append(sign(p, KEYS[os],
                              g.PROVIDER_DOMAIN + os.encode() + b"\x00"))
        provenance[os] = {
            "repository": "spoonman136668-ai/FORGE",
            "run_id": RUN, "job_id": p["provider_job_id"],
            "runner_os": os, "artifact_sha256": p["artifact_sha256"],
            "run_attempt": 1, "conclusion": "success",
            "source_sha": g.SOURCE, "authenticated_from_github": True}
    return g32, sign(o, OWNER_KEY, g.OWNER_DOMAIN), providers, provenance


def verify(args, owner_key=OWNER_KEY, keys=KEYS):
    return g.verify_contract(*args, owner_key=owner_key, provider_keys=keys)


def resign(args, i, field, value):
    args[2][i]["binding"][field] = value
    os = args[2][i]["binding"]["runner_os"]
    args[2][i] = sign(args[2][i]["binding"], KEYS[os],
                      g.PROVIDER_DOMAIN + os.encode() + b"\x00")


def resign_owner(args, field, value):
    args[1]["binding"][field] = value
    args[1] = sign(args[1]["binding"], OWNER_KEY, g.OWNER_DOMAIN)


class G33ContractTests(unittest.TestCase):
    def test_version_distinct_hmac_contract_does_not_grant_live_authority(self):
        r = verify(fixture())
        self.assertTrue(r["signature_contract_fixtures_valid"])
        for key in ("candidate_signed_real_provider_proof",
                    "actual_original_sqlite_owner_signature_verified",
                    "genuine_provider_zip_verified", "native_qualified",
                    "original_owner_consumed", "production_release_authorized",
                    "scientific_first_use"):
            self.assertIs(r[key], False)

    def test_g32_both_original_negative_reports_cannot_be_promoted(self):
        left = g32_report()
        right = copy.deepcopy(left)
        self.assertTrue(g.inspect_real_g32_pair(left, right)
                        ["g32_historical_negative_preserved"])
        right["native_qualified"] = True
        with self.assertRaises(g.G33Denied):
            g.inspect_real_g32_pair(left, right)
        for field, value in [
            ("original_owner_consumed", True),
            ("provider_receipt_signed", True),
            ("production_release_authorized", True),
            ("scientific_first_use", True),
            ("source_run_id", g.ORIGINAL_FAILED_RUN)]:
            changed = g32_report()
            changed[field] = value
            with self.subTest(field=field), self.assertRaises(g.G33Denied):
                g.inspect_real_g32_pair(changed, left)

    def test_bad_owner_hmac_and_cross_protocol_version_rejected(self):
        for mut in [
            lambda a: a[1].update({"hmac_sha256": "f"*64}),
            lambda a: a[1]["binding"].update(
                {"schema": "forge.f139.nci04.native-execution-receipt.v2"}),
            lambda a: a[1].update({"hmac_sha256": "invalid"}),
        ]:
            args = list(fixture())
            mut(args)
            with self.assertRaises(g.G33Denied):
                verify(args)

    def test_no_owner_or_provider_secret_alias_and_no_malformed_keys(self):
        for keys in [
            {"ubuntu-latest": OWNER_KEY, "windows-latest": WIN_KEY},
            {"ubuntu-latest": LINUX_KEY, "windows-latest": LINUX_KEY},
            {"ubuntu-latest": b"x", "windows-latest": WIN_KEY},
            {"ubuntu-latest": LINUX_KEY},
        ]:
            with self.subTest(keys=tuple(keys)), self.assertRaises(g.G33Denied):
                verify(fixture(), keys=keys)

    def test_replayed_terminal_original_issue_or_run_rejected(self):
        for field, value in [
            ("original_event_seq", g.ORIGINAL_TERMINAL_SEQ),
            ("issue_number", g.ORIGINAL_FAILED_ISSUE),
            ("provider_run_id", g.ORIGINAL_FAILED_RUN),
            ("provider_run_id", g.DIAGNOSTIC_RUN),
            ("original_event_sha256", "bad"),
            ("owner_source_sha", "0"*40),
            ("target_commit", "0"*40),
            ("target_tree", "0"*40),
            ("path", "scripts/other.py"),
            ("scientific_first_use", True),
            ("development_only", False),
            ("paid_model_calls", 1),
            ("accepted_ref_mutations", 1),
        ]:
            args = list(fixture())
            resign_owner(args, field, value)
            with self.subTest(field=field), self.assertRaises(g.G33Denied):
                verify(args)

    def test_provider_negative_matrix_signed_under_test_only_key(self):
        for field, value in [
            ("baseline_g29_pass_count", 0),
            ("baseline_full_pass_count", 0),
            ("candidate_g29_expected_negative_count", 0),
            ("candidate_applicable_test_count", 0),
            ("candidate_test_module_count", 0),
            ("candidate_compiled", False),
            ("child_cpu_measured", False),
            ("child_rss_measured", False),
            ("resource_budget_enforced", False),
            ("native_qualified", False),
            ("scientific_first_use", True),
            ("accepted_ref_mutations", 1),
            ("paid_model_calls", 1),
            ("qualification_key", "0"*64),
            ("candidate_after_sha256", "0"*64),
            ("target_commit", "0"*40),
            ("owner_event_sha256", "0"*64),
            ("provider_run_id", g.ORIGINAL_FAILED_RUN),
            ("artifact_sha256", "not-a-digest"),
        ]:
            args = list(fixture())
            resign(args, 0, field, value)
            with self.subTest(field=field), self.assertRaises(g.G33Denied):
                verify(args)

    def test_cross_os_forgery_duplicate_and_missing_host_rejected(self):
        for change in [
            lambda a: a[2].pop(),
            lambda a: a[2].append(copy.deepcopy(a[2][0])),
            lambda a: a[2].__setitem__(1, copy.deepcopy(a[2][0])),
            lambda a: a[2][0].update({"hmac_sha256": "a"*64}),
            lambda a: a[3]["windows-latest"].update({"run_attempt": 2}),
            lambda a: a[3]["windows-latest"].update(
                {"authenticated_from_github": False}),
            lambda a: a[3]["windows-latest"].update(
                {"source_sha": "0"*40}),
            lambda a: a[3]["windows-latest"].update(
                {"artifact_sha256": "0"*64}),
        ]:
            args = list(fixture())
            change(args)
            with self.assertRaises(g.G33Denied):
                verify(args)

    def test_even_valid_signatures_fail_without_independent_provider_identity(self):
        args = list(fixture())
        resign(args, 1, "provider_job_id", args[2][0]["binding"]
               ["provider_job_id"])
        args[3]["windows-latest"]["job_id"] = args[3]["ubuntu-latest"]["job_id"]
        with self.assertRaises(g.G33Denied):
            verify(args)
        args = list(fixture())
        resign(args, 1, "artifact_sha256", args[2][0]["binding"]
               ["artifact_sha256"])
        args[3]["windows-latest"]["artifact_sha256"] = (
            args[3]["ubuntu-latest"]["artifact_sha256"])
        with self.assertRaises(g.G33Denied):
            verify(args)


if __name__ == "__main__":
    unittest.main()
