"""G32 source-only artifact ZIP + Actions metadata custody negative matrix."""
import copy
import io
import json
import unittest
from unittest.mock import patch
import zipfile

from f139 import nci04_v19_g32_artifact_custody as g32
from f139.test_nci04_v19_g31_diagnostic_reconcile import fixture


def zip_of(name, payload):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr(name, payload)
    return buf.getvalue()


def sample():
    linux = zip_of(g32.EXPECTED["linux"][2], g32.canonical(fixture("linux")))
    windows = zip_of(g32.EXPECTED["windows"][2], g32.canonical(fixture("windows")))
    defs = {}
    items = []
    for platform, raw in (("linux", linux), ("windows", windows)):
        ident, name, member, _ = g32.EXPECTED[platform]
        digest = g32.sha(raw)
        defs[platform] = (ident, name, member, digest)
        items.append({
            "id": ident, "name": name, "digest": "sha256:" + digest,
            "expired": False, "size_in_bytes": len(raw),
            "archive_download_url": (
                "https://api.github.com/repos/" + g32.REPO +
                "/actions/artifacts/" + str(ident) + "/zip"),
            "workflow_run": {"id": g32.RUN, "head_sha": g32.SOURCE},
        })
    run = {
        "id": g32.RUN, "head_sha": g32.SOURCE, "head_branch": g32.BRANCH,
        "event": "push", "run_attempt": 1, "status": "completed",
        "conclusion": "success", "actor": {"login": "spoonman136668-ai"},
        "repository": {"full_name": g32.REPO},
        "head_repository": {"full_name": g32.REPO},
    }
    return defs, run, {"total_count": len(items), "artifacts": items}, linux, windows


def run_sample(defs, run, artifact_list, linux, windows):
    with patch.dict(g32.EXPECTED, defs):
        return g32.verify(g32.canonical(run), g32.canonical(artifact_list),
                          linux, windows)


class G32ArtifactTests(unittest.TestCase):
    def setUp(self):
        self.defs, self.run, self.artifacts, self.linux, self.windows = sample()

    def good(self):
        return run_sample(self.defs, self.run, self.artifacts,
                          self.linux, self.windows)

    def test_positive_synthetic_artifact_reconciliation_is_non_authoritative(self):
        r = self.good()
        self.assertEqual(r["source_run_id"], g32.RUN)
        self.assertEqual(r["diagnostic"]["windows_historical_regression"],
                         "NEGATIVE_RETAINED")
        for field in ("provider_receipt_signed", "original_owner_consumed",
                      "native_qualified", "full_native_worker_regression_qualified",
                      "production_release_authorized", "scientific_first_use"):
            self.assertIs(r[field], False)

    def test_reject_run_identity_and_provenance_drift(self):
        cases = [
            ("id", g32.RUN + 1), ("head_sha", "0" * 40),
            ("head_branch", "main"), ("event", "workflow_dispatch"),
            ("run_attempt", 2), ("status", "in_progress"),
            ("conclusion", "failure"),
        ]
        for key, value in cases:
            with self.subTest(key=key):
                run = copy.deepcopy(self.run)
                run[key] = value
                with self.assertRaises(g32.G32Denied):
                    run_sample(self.defs, run, self.artifacts, self.linux,
                               self.windows)
        for key in ("actor", "repository", "head_repository"):
            with self.subTest(key=key):
                run = copy.deepcopy(self.run)
                run[key] = {"login": "imposter", "full_name": "other/repo"}
                with self.assertRaises(g32.G32Denied):
                    run_sample(self.defs, run, self.artifacts, self.linux,
                               self.windows)

    def test_reject_artifact_duplicate_missing_wrong_digest_and_expiry(self):
        mutations = [
            lambda x: x["artifacts"].append(copy.deepcopy(x["artifacts"][0])),
            lambda x: x["artifacts"].pop(),
            lambda x: x["artifacts"][0].update({"digest": "sha256:" + "0" * 64}),
            lambda x: x["artifacts"][0].update({"expired": True}),
            lambda x: x["artifacts"][0].update({"id": 11}),
            lambda x: x["artifacts"][1].update({"size_in_bytes": 0}),
            lambda x: x["artifacts"][0]["workflow_run"].update({"id": 2}),
            lambda x: x["artifacts"][1]["workflow_run"].update(
                {"head_sha": "0" * 40}),
            lambda x: x["artifacts"][1].update(
                {"archive_download_url": "https://example.com/fake"}),
        ]
        for i, mut in enumerate(mutations):
            with self.subTest(mutation=i):
                a = copy.deepcopy(self.artifacts)
                mut(a)
                with self.assertRaises(g32.G32Denied):
                    run_sample(self.defs, self.run, a, self.linux,
                               self.windows)

    def test_reject_zip_tamper_and_cross_os_swap(self):
        cases = [
            (self.linux + b"altered", self.windows),
            (self.windows, self.linux),
            (self.linux[:-9], self.windows),
            (b"not a zip", self.windows),
        ]
        for n, (l, w) in enumerate(cases):
            with self.subTest(case=n), self.assertRaises(g32.G32Denied):
                run_sample(self.defs, self.run, self.artifacts, l, w)

    def test_reject_traversal_extra_files_and_forged_native_success(self):
        malformed = [
            zip_of("../unsafe.json", g32.canonical(fixture("linux"))),
            zip_of("extra.json", g32.canonical(fixture("linux"))),
            zip_of(g32.EXPECTED["linux"][2], b"invalid json"),
        ]
        bad = fixture("linux")
        bad["signed_provider_success"] = True
        malformed.append(zip_of(g32.EXPECTED["linux"][2],
                                g32.canonical(bad)))
        for i, raw in enumerate(malformed):
            with self.subTest(case=i):
                definitions = dict(self.defs)
                ident, name, member, _ = definitions["linux"]
                definitions["linux"] = (ident, name, member, g32.sha(raw))
                art = copy.deepcopy(self.artifacts)
                art["artifacts"][0]["digest"] = "sha256:" + g32.sha(raw)
                art["artifacts"][0]["size_in_bytes"] = len(raw)
                with self.assertRaises(g32.G32Denied):
                    run_sample(definitions, self.run, art, raw, self.windows)

    def test_reject_empty_or_malformed_metadata(self):
        with patch.dict(g32.EXPECTED, self.defs):
            for value in (b"", b"{invalid", b"[]", b"null"):
                with self.subTest(value=value), self.assertRaises(g32.G32Denied):
                    g32.verify(value, g32.canonical(self.artifacts),
                               self.linux, self.windows)

    def test_distinct_reports_and_windows_negative_are_required(self):
        w = fixture("windows")
        w["baseline_full_unmodified_regression_pass"] = True
        replaced = zip_of(g32.EXPECTED["windows"][2], g32.canonical(w))
        definitions = dict(self.defs)
        ident, name, member, _ = definitions["windows"]
        definitions["windows"] = (ident, name, member, g32.sha(replaced))
        art = copy.deepcopy(self.artifacts)
        art["artifacts"][1]["digest"] = "sha256:" + g32.sha(replaced)
        art["artifacts"][1]["size_in_bytes"] = len(replaced)
        with self.assertRaises(g32.G32Denied):
            run_sample(definitions, self.run, art, self.linux, replaced)


    def test_exact_windows_crlf_serialization_without_broad_normalization(self):
        raw = zip_of(g32.EXPECTED["windows"][2],
                     g32.canonical(fixture("windows")).replace(b"\\n", b"\\r\\n"))
        definitions = dict(self.defs)
        ident, name, member, _ = definitions["windows"]
        definitions["windows"] = (ident, name, member, g32.sha(raw))
        art = copy.deepcopy(self.artifacts)
        art["artifacts"][1]["digest"] = "sha256:" + g32.sha(raw)
        art["artifacts"][1]["size_in_bytes"] = len(raw)
        result = run_sample(definitions, self.run, art, self.linux, raw)
        self.assertFalse(result["native_qualified"])
        self.assertEqual(result["diagnostic"]["windows_historical_regression"],
                         "NEGATIVE_RETAINED")

        bad = zip_of(g32.EXPECTED["windows"][2],
                     g32.canonical(fixture("windows")).replace(b"\\n", b"\\r\\r\\n"))
        definitions["windows"] = (ident, name, member, g32.sha(bad))
        art["artifacts"][1]["digest"] = "sha256:" + g32.sha(bad)
        art["artifacts"][1]["size_in_bytes"] = len(bad)
        with self.assertRaises(g32.G32Denied):
            run_sample(definitions, self.run, art, self.linux, bad)

    def test_linux_crlf_is_not_accepted_even_with_forged_matching_zip_digest(self):
        raw = zip_of(g32.EXPECTED["linux"][2],
                     g32.canonical(fixture("linux")).replace(b"\\n", b"\\r\\n"))
        definitions = dict(self.defs)
        ident, name, member, _ = definitions["linux"]
        definitions["linux"] = (ident, name, member, g32.sha(raw))
        art = copy.deepcopy(self.artifacts)
        art["artifacts"][0]["digest"] = "sha256:" + g32.sha(raw)
        art["artifacts"][0]["size_in_bytes"] = len(raw)
        with self.assertRaises(g32.G32Denied):
            run_sample(definitions, self.run, art, raw, self.windows)


if __name__ == "__main__":
    unittest.main()
