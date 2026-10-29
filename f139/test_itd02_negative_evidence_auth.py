"""Synthetic fail-closed tests only; no original owner, network, dispatch, or science."""
import base64
import hashlib
import unittest
from unittest.mock import patch
from f139 import itd02_negative_evidence_auth as evidence


def git_blob(raw):
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


class EvidenceAuthenticationTests(unittest.TestCase):
    def fixture(self):
        raw = (b"Yggdrasil source-bound evidence: failed to generalize. "
               b"Not in that manifest.\n")
        return raw, {
            "type": "file", "encoding": "base64", "sha": git_blob(raw),
            "size": len(raw), "content": base64.b64encode(raw).decode()
        }

    def test_exact_source_is_read_only_and_unadmitted(self):
        raw, item = self.fixture()
        with patch.object(evidence, "BLOB_SHA", git_blob(raw)):
            got = evidence.authenticate(lambda route: item)
        self.assertEqual(got["status"], "AUTHENTICATED_UNADMITTED")
        self.assertEqual(got["content_sha256"], hashlib.sha256(raw).hexdigest())
        for flag in ("steering_manifest_admitted", "candidate_selection_authorized",
                     "dispatch_authorized", "scientific_first_use",
                     "accepted_ref_mutation"):
            self.assertFalse(got[flag])

    def test_mismatched_sha_denied(self):
        raw, item = self.fixture()
        with self.assertRaisesRegex(evidence.EvidenceDenied, "SOURCE_METADATA_INVALID"):
            evidence.authenticate(lambda route: item)

    def test_mutated_bytes_denied_even_if_metadata_matches(self):
        raw, item = self.fixture()
        with patch.object(evidence, "BLOB_SHA", git_blob(raw)):
            item["content"] = base64.b64encode(b"altered").decode()
            with self.assertRaisesRegex(evidence.EvidenceDenied, "SOURCE_IDENTITY_DRIFT"):
                evidence.authenticate(lambda route: item)

    def test_wrong_source_route_cannot_be_silently_replaced(self):
        raw, item = self.fixture()
        expected = (f"repos/{evidence.REPOSITORY}/contents/{evidence.PATH}"
                    f"?ref={evidence.SOURCE_COMMIT}")
        with patch.object(evidence, "BLOB_SHA", git_blob(raw)):
            evidence.authenticate(lambda route: item if route == expected else None)

    def test_unrelated_document_denied(self):
        raw = b"random unrelated notes\n"
        item = {"type": "file", "encoding": "base64", "sha": git_blob(raw),
                "size": len(raw), "content": base64.b64encode(raw).decode()}
        with patch.object(evidence, "BLOB_SHA", git_blob(raw)):
            with self.assertRaisesRegex(evidence.EvidenceDenied, "SOURCE_SCOPE_INVALID"):
                evidence.authenticate(lambda route: item)


if __name__ == "__main__":
    unittest.main()
