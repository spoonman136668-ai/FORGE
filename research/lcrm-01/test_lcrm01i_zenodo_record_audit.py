"""Source-only fixtures; no remote or original dataset is ever used."""
import copy
import unittest
import lcrm01i_zenodo_record_audit as a


def fixture():
    def file(key):
        return {"key": key, "size": 135, "checksum": "md5:" + "a" * 32,
                "links": {"self": "https://zenodo.org/api/records/23095083/files/" + key}}
    return {"id": 23095083, "doi": a.EXPECTED_DOI,
            "metadata": {"title": "DoTime — dot-Identifiability-v1 (v1.2.0)",
                         "version": "1.2.0", "license": {"id": "cc-by-4.0"}},
            "files": [file("manifest.json"), file("shard-0000.parquet")]}


class ZenodoReleaseMetadataBoundary(unittest.TestCase):
    def test_unavailable_source_does_not_mint_trust(self):
        self.assertEqual(a.inspect_record(None)["status"], "PROVIDER_RECORD_NOT_RETRIEVED")
    def test_mock_well_formed_record_is_never_authenticated(self):
        v = a.inspect_record(fixture())
        self.assertEqual(v["status"], "PROVIDER_METADATA_SHAPE_CONSISTENT_RAW_BYTES_UNVERIFIED")
        self.assertEqual(len(v["listed_files"]), 2)
        self.assertFalse(v["scientific_firstuse_authorized"])
        self.assertFalse(v["provider_http_origin_authenticated"])
        self.assertFalse(v["provider_raw_bytes_verified"])
    def test_deterministic_hash_not_independent_pin(self):
        self.assertEqual(a.inspect_record(fixture())["metadata_canonical_sha256"],
                         a.inspect_record(fixture())["metadata_canonical_sha256"])
        self.assertFalse(a.inspect_record(fixture())["independent_source_birth_verified"])
    def test_different_or_concept_doi_denied(self):
        for doi in ("10.5281/zenodo.20846063", "10.5281/zenodo.22673322", "10.5281/zenodo.20919553"):
            x = fixture(); x["doi"] = doi
            self.assertEqual(a.inspect_record(x)["status"], "DENY_CONCEPT_OR_OTHER_VERSION_DOI")
    def test_wrong_record_denied(self):
        for value in (23095082, "23095083", True):
            x = fixture(); x["id"] = value
            self.assertEqual(a.inspect_record(x)["status"], "DENY_WRONG_EXACT_RECORD_ID")
    def test_version_and_suite_drift_denied(self):
        for title, version in (("Other dataset", "1.2.0"), ("dot-Identifiability-v1", "latest"),
                               ("dot-Identifiability-v1", "1.1.0")):
            x = fixture(); x["metadata"].update(title=title, version=version)
            self.assertEqual(a.inspect_record(x)["status"], "DENY_SUITE_OR_VERSION_MISMATCH")
    def test_missing_metadata_denied(self):
        x = fixture(); x.pop("metadata")
        self.assertEqual(a.inspect_record(x)["status"], "DENY_NO_PROVIDER_METADATA")
    def test_license_is_explicit_not_assumed(self):
        for license in ({}, {"id": "MIT"}, "", None):
            x = fixture(); x["metadata"]["license"] = license
            self.assertEqual(a.inspect_record(x)["status"], "DENY_RELEASE_LICENSE_NOT_CONFIRMED")
    def test_missing_inventory_denied(self):
        x = fixture(); x["files"] = []
        self.assertEqual(a.inspect_record(x)["status"], "DENY_MISSING_PROVIDER_FILE_INVENTORY")
    def test_duplicate_and_traversal_paths_denied(self):
        for value in ("../shard-0001.parquet", "/manifest.json", "a/./manifest.json", "manifest.json"):
            x = fixture(); x["files"][1]["key"] = value
            self.assertEqual(a.inspect_record(x)["status"], "DENY_MALFORMED_OR_DUPLICATE_FILENAME")
    def test_nonpositive_boolean_oversize_rejected(self):
        for value in (0, -1, True, 10**15):
            x = fixture(); x["files"][1]["size"] = value
            self.assertEqual(a.inspect_record(x)["status"], "DENY_INVALID_PROVIDER_FILE_SIZE")
    def test_wrong_checksum_or_absent_denied(self):
        for value in (None, "a" * 32, "sha256:" + "f" * 64, "md5:" + "g" * 32):
            x = fixture(); x["files"][1]["checksum"] = value
            self.assertEqual(a.inspect_record(x)["status"], "DENY_MISSING_OR_INVALID_MD5_CLAIM")
    def test_untrusted_http_link_denied(self):
        for link in ("http://zenodo.org/x", "https://evil.org/x", "https://zenodo.org.evil.org/x", "file:///tmp/a"):
            x = fixture(); x["files"][1]["links"]["self"] = link
            self.assertEqual(a.inspect_record(x)["status"], "DENY_UNTRUSTED_FILE_LINK")
    def test_no_manifest_denied(self):
        x = fixture(); x["files"][0]["key"] = "metadata.json"
        self.assertEqual(a.inspect_record(x)["status"], "DENY_NO_RELEASE_MANIFEST_OR_PARQUET_SHARDS")
    def test_no_parquet_denied(self):
        x = fixture(); x["files"][1]["key"] = "metadata.json"
        self.assertEqual(a.inspect_record(x)["status"], "DENY_NO_RELEASE_MANIFEST_OR_PARQUET_SHARDS")
    def test_malformed_rows_rejected(self):
        x = fixture(); x["files"][0] = 5
        self.assertEqual(a.inspect_record(x)["status"], "DENY_INVALID_FILE_ROW")
    def test_no_causal_or_scientific_admission_even_all_metadata_positive(self):
        x = fixture(); x["experimental_randomization_certified"] = True
        v = a.inspect_record(x)
        for field in ("shared_exogenous_noise_verified", "provider_raw_bytes_verified",
                      "independent_source_birth_verified", "scientific_firstuse_authorized"):
            self.assertFalse(v[field])
        self.assertEqual(v["original_scientific_firstuse_consumed"], 0)

if __name__ == "__main__": unittest.main()
