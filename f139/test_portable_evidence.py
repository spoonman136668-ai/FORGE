"""F139 G4 bounded portable receipt adversarial validation (no owner writes)."""
import copy
import json
import unittest

V1 = "forge.f139.owner-native-provider-negative.v1"
V2 = "forge.f139.owner-native-provider-negative.v2"

from f139.portable_evidence import (
    SCHEMA, ZERO, PortableEvidenceDenied,
    canonical, seal_body, sha, verify_portable_receipt,
)

TICKET = "f139-nci04-i856-52e007e83be0-51b67e31"
SOURCE = "52e007e83be08b851283fc4a6e213ea506469f43"


def fixture():
    head = ZERO
    headers = []
    for seq in range(1, 191):
        if seq == 188:
            kind = "NATIVE_DEVELOPMENT_ADMITTED"
            payload = {"ticket": TICKET, "only_for_mock": True}
        elif seq == 189:
            kind = "ATTEMPT_QUARANTINED"
            payload = {"ticket": TICKET,
                       "reason": "FAILED_OR_CANCELLED_NO_REPLAY"}
        elif seq == 190:
            kind = "NATIVE_FAILED_PROVIDER_CUSTODY"
            report = {
                "ticket": TICKET, "run_id": 40081353365,
                "source_sha": SOURCE,
                "provider_terminal": "FAILURE_NO_REPLAY",
                "scientific_first_use": False,
                "jobs": {
                    "windows-latest": {"job_id": 120835487661, "conclusion": "failure"},
                    "ubuntu-latest": {"job_id": 120835487668, "conclusion": "failure"}},
                "artifact_ids": [12555024083, 12555357162],
            }
            payload = {
                "schema": V2, "ticket": TICKET, "run_id": 40081353365,
                "source_sha": SOURCE, "provider_sha256": sha(report),
                "scientific_first_use": False, "provider": report,
                "quarantine_event_seq": quarantine["seq"],
                "quarantine_event_sha256": quarantine["sha"],
            }
        else:
            kind = "HISTORIC_EVENT"
            payload = {"index": seq}
        entry = {"seq": seq, "prior_sha": head, "kind": kind,
                 "payload": payload}
        h = sha(entry)
        headers.append({"seq": seq, "prior_sha": head, "sha": h})
        head = h
        if seq == 188:
            admission = {"seq": seq, "prior_sha": headers[-1]["prior_sha"],
                         "sha": h, "kind": kind}
        if seq in (189, 190):
            obj = {"seq": seq, "prior_sha": headers[-1]["prior_sha"],
                   "sha": h, "kind": kind, "payload": payload}
            if seq == 189:
                quarantine = obj
            else:
                failure = obj
    return {
        "schema": SCHEMA,
        "owner_source_sha": SOURCE,
        "owner_head_seq": 190,
        "owner_head_sha": head,
        "scientific_first_use": False,
        "target_ticket": TICKET,
        "target_source_sha": SOURCE,
        "task_stages": {"QUARANTINED": 11, "VERIFIED": 18},
        "event_headers": headers,
        "target_events": [admission, quarantine, failure],
    }


def fixture_v1():
    """Original v1 negative: provider event immediately before quarantine."""
    body = fixture()
    admission, quarantine, failure = body["target_events"]
    payload = copy.deepcopy(failure["payload"])
    payload["schema"] = V1
    del payload["quarantine_event_seq"]
    del payload["quarantine_event_sha256"]
    prior = body["event_headers"][187]["sha"]
    for seq, kind, doc in ((189, "NATIVE_FAILED_PROVIDER_CUSTODY", payload),
                           (190, "ATTEMPT_QUARANTINED", quarantine["payload"])):
        h = sha({"seq": seq, "prior_sha": prior, "kind": kind, "payload": doc})
        entry = {"seq": seq, "prior_sha": prior, "sha": h}
        body["event_headers"][seq - 1] = entry
        target = failure if kind == "NATIVE_FAILED_PROVIDER_CUSTODY" else quarantine
        target.update(entry)
        if kind == "NATIVE_FAILED_PROVIDER_CUSTODY":
            target["payload"] = payload
        prior = h
    body["owner_head_sha"] = prior
    return body


class PortableEvidenceTests(unittest.TestCase):
    def read(self, body):
        return verify_portable_receipt(
            canonical(seal_body(body)), expected_ticket=TICKET,
            expected_source=SOURCE)

    def test_valid_internal_commitments_not_a_trust_anchor(self):
        r = self.read(fixture())
        self.assertEqual(r["head_seq"], 190)
        self.assertEqual(r["quarantined"], 11)
        self.assertFalse(r["scientific_first_use"])
        self.assertEqual(r["original_custody_trust"],
                         "REQUIRES_INDEPENDENT_GITHUB_ATTESTATION")

    def test_valid_original_v1_provider_before_quarantine(self):
        verified = self.read(fixture_v1())
        self.assertEqual(verified["provider_run_id"], 40081353365)
        self.assertEqual(verified["head_seq"], 190)

    def test_v1_nonadjacent_provider_quarantine_denied(self):
        body = fixture_v1()
        body["target_events"][1]["seq"] = 188
        with self.assertRaises(PortableEvidenceDenied):
            self.read(body)

    def test_v2_quarantine_binding_denied(self):
        body = fixture()
        body["target_events"][2]["payload"]["quarantine_event_sha256"] = "a"*64
        with self.assertRaises(PortableEvidenceDenied):
            self.read(body)

    def denied(self, change, label):
        body = fixture()
        change(body)
        with self.assertRaisesRegex(PortableEvidenceDenied, label):
            self.read(body)

    def test_earlier_head_drift_is_not_accepted(self):
        self.denied(lambda b: b.update(owner_head_sha="a"*64),
                    "HEAD_MISMATCH")
        self.denied(lambda b: b["event_headers"][50].update(
            prior_sha="a"*64), "HEADER_DISCONTINUITY")

    def test_duplicate_or_reordered_target_is_denied(self):
        self.denied(lambda b: b["target_events"].append(
            copy.deepcopy(b["target_events"][2])), "TARGET_EVENT_COUNT")
        self.denied(lambda b: b["target_events"][1].update(
            seq=188), "TARGET_EVENT_HEADER_MISMATCH")

    def test_payload_and_stage_tampering_fail(self):
        self.denied(lambda b: b["target_events"][1]["payload"].update(
            reason="GOOD"), "TARGET_EVENT_PAYLOAD_TAMPERED")
        self.denied(lambda b: b["task_stages"].update(
            QUARANTINED=10), "STAGE_COUNTERS_INVALID")
        self.denied(lambda b: b["target_events"][2]["payload"]["provider"][
            "jobs"]["ubuntu-latest"].update(conclusion="success"),
            "TARGET_EVENT_PAYLOAD_TAMPERED")

    def test_science_or_identity_escalation_fail(self):
        self.denied(lambda b: b.update(scientific_first_use=True),
                    "RECEIPT_IDENTITY")
        self.denied(lambda b: b.update(owner_source_sha="1"*40),
                    "SOURCE_PIN_DRIFT")
        self.denied(lambda b: b.update(target_ticket=TICKET+"x"),
                    "RECEIPT_IDENTITY")

    def test_noncanonical_duplicate_and_digest_fail(self):
        body = fixture()
        document = seal_body(body)
        with self.assertRaisesRegex(PortableEvidenceDenied, "NONCANONICAL"):
            verify_portable_receipt(json.dumps(document).encode(),
                                    expected_ticket=TICKET)
        document["body_sha256"] = "a"*64
        with self.assertRaisesRegex(PortableEvidenceDenied, "NONCANONICAL"):
            verify_portable_receipt(canonical(document))
        raw = canonical(seal_body(body)).decode()
        corrupted = raw.replace('"body_sha256"', '"body_sha256"')
        self.assertEqual(raw, corrupted)
        duplicate = raw.replace('"body_sha256":', '"body_sha256":"a","body_sha256":', 1)
        with self.assertRaisesRegex(PortableEvidenceDenied, "DUPLICATE_JSON_KEY"):
            verify_portable_receipt(duplicate.encode())

    def test_signer_required_no_shared_secret_in_bundle(self):
        raw = canonical(seal_body(fixture()))
        for word in (b'"key"', b'"signature"', b'"secret"', b'OWNER_HMAC'):
            self.assertNotIn(word, raw)


if __name__ == "__main__":
    unittest.main()
