"""Source qualification for the inert, manual-only F139 custody runner admission."""
import hashlib
from pathlib import Path
import unittest

from f139.custody_host_probe import AdmissionBlocked, source_admission, host_observation


MAIN="5ca118a0425dd4c6b3fa67a2f575cfda491cb8ba"
HEAD="d"*64
HOST="FORGE-ISOLATED-TEST-WINDOWS"
MACHINE=hashlib.sha256(HOST.upper().encode()).hexdigest()


def evidence():
    return {
        "repository":"spoonman136668-ai/FORGE","event":"workflow_dispatch",
        "ref":"refs/heads/main","main":MAIN,"request_source":MAIN,
        "request_head":HEAD,"pinned_source":MAIN,"pinned_head":HEAD,
        "pinned_machine":MACHINE,"isolation_declared":"true",
        "runner_name":"FORGE-CODEX-REMOTE","runner_os":"Windows","hostname":HOST,
    }


class PreflightTests(unittest.TestCase):
    def test_declared_pins_are_not_custody_or_independent_isolation(self):
        result=source_admission(evidence())
        self.assertEqual(result["workstation_reads"],0)
        self.assertFalse(result["historical_custody_verified"])
        self.assertEqual(result["controller_actions"],0)
        host=host_observation(evidence())
        self.assertIn("NOT_INDEPENDENTLY_VERIFIED",host["disposition"])
        self.assertEqual(host["machine_sha256"],MACHINE)
        self.assertEqual(host["research_jobs_started"],0)

    def test_fail_closed_unsigned_head_and_missing_witness(self):
        for field,value in (
            ("request_head","e"*64),("pinned_head",""),
            ("isolation_declared","false"),("pinned_machine",""),
            ("request_source","f"*40),("main","f"*40),
            ("event","push"),("ref","refs/heads/proposal/other"),
            ("repository","somebody/other"),
        ):
            case=evidence();case[field]=value
            with self.subTest(field=field),self.assertRaises(AdmissionBlocked):
                source_admission(case)

    def test_runner_and_machine_drift_fail_closed(self):
        for field,value in (
            ("runner_name","FORGE-RESEARCH-REMOTE"),("runner_os","Linux"),
            ("hostname","DIFFERENT-MACHINE"),("pinned_machine","f"*64),
            ("request_head","0"*64),("request_source","0"*40),
            ("isolation_declared",""),("event","schedule"),
        ):
            case=evidence();case[field]=value
            with self.subTest(field=field),self.assertRaises(AdmissionBlocked):
                host_observation(case)

    def test_workflow_is_manual_only_and_does_not_launch_controller(self):
        workflow=(Path(__file__).parents[1] /
            ".github/workflows/forge-f139-custody-host-preflight.yml").read_text()
        self.assertIn("workflow_dispatch:",workflow)
        self.assertNotIn("\n  schedule:",workflow)
        self.assertNotIn("\n  push:",workflow)
        self.assertNotIn("\n  pull_request:",workflow)
        self.assertIn("forge-codex-isolated",workflow)
        self.assertIn("F139_CUSTODY_DEDICATED_RUNNER_QUALIFIED",workflow)
        self.assertNotIn("local_controller --db",workflow)
        self.assertNotIn("audit_d2k_custody --db",workflow)
        self.assertNotIn("secrets.F139_WORKER_HMAC_KEY",workflow)
        self.assertIn("RUNNER_IDENTITY_OBSERVATION_ONLY",workflow)


if __name__=="__main__": unittest.main()
