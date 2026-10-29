import unittest
from f139.v19_origin_release_admission import (
    ReleaseAdmissionDenied, assess_v19_origin,
)
ORIGIN = "db7a1d0f324478183c54df417624053448d6b08b"
TARGET = "a" * 40

def good():
    return dict(attested_origin_source=ORIGIN, installed_source=ORIGIN, policy_source=ORIGIN,
                ledger_source=ORIGIN, main_source=TARGET,
                checkout_source=TARGET, release_source=TARGET,
                immutable_rule_verified=True, original_owner_verified=True,
                no_inflight=True, cold_restore_verified=True,
                scientific_first_use=False)

class AdmissionTests(unittest.TestCase):
    def test_complete_read_only_admission_never_authorizes_execution(self):
        result = assess_v19_origin(**good())
        self.assertEqual(result["status"], "READ_ONLY_ADMISSIBLE_NOT_AUTHORIZED")
        self.assertFalse(result["execute_authorized"])

    def test_every_sha_identity_fails_closed(self):
        for key in ("attested_origin_source", "installed_source", "policy_source", "ledger_source",
                    "main_source", "checkout_source", "release_source"):
            with self.subTest(key=key):
                bad=good();bad[key]="b"*40
                with self.assertRaises(ReleaseAdmissionDenied):
                    assess_v19_origin(**bad)

    def test_every_custody_control_fails_closed(self):
        for key in ("immutable_rule_verified", "original_owner_verified",
                    "no_inflight", "cold_restore_verified"):
            for value in (False, None, "true"):
                with self.subTest(key=key,value=value):
                    bad=good();bad[key]=value
                    with self.assertRaises(ReleaseAdmissionDenied):
                        assess_v19_origin(**bad)

    def test_science_and_noop_denied(self):
        for value in (True, None, "false"):
            bad=good();bad["scientific_first_use"]=value
            with self.assertRaises(ReleaseAdmissionDenied):
                assess_v19_origin(**bad)
        bad=good()
        for key in ("main_source","checkout_source","release_source"):
            bad[key]=ORIGIN
        with self.assertRaises(ReleaseAdmissionDenied):
            assess_v19_origin(**bad)

    def test_old_origin_source_mismatch_denied(self):
        bad=good();bad["attested_origin_source"]="0743ca22b76ebd943a66f05a36ea919301676be0"
        with self.assertRaises(ReleaseAdmissionDenied):
            assess_v19_origin(**bad)

if __name__=="__main__":
    unittest.main()
