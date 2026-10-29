import unittest
from f139.v19_origin_release_admission import (
    V19_ORIGIN, ReleaseAdmissionDenied, assess_v19_origin,
)
TARGET = "a" * 40

def good():
    return dict(installed_source=V19_ORIGIN, policy_source=V19_ORIGIN,
                ledger_source=V19_ORIGIN, main_source=TARGET,
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
        for key in ("installed_source", "policy_source", "ledger_source",
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
            bad[key]=V19_ORIGIN
        with self.assertRaises(ReleaseAdmissionDenied):
            assess_v19_origin(**bad)

if __name__=="__main__":
    unittest.main()
