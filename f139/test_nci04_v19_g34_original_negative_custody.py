"""G34 source-only negative controls for genuine old owner/provider custody."""
import copy
import json
import unittest

from f139 import nci04_v19_g34_original_negative_custody as g


def owner_fixture():
    evidence = {
        "schema": "forge.f139.v19.i1138.postfailed-custody.readonly.v1",
        "source_sha": g.OWNER_SOURCE,
        "issue": 1138, "ticket": g.TICKET,
        "original_run": g.PROVIDER_RUN, "head_seq": 322,
        "head_sha256": g.OWNER_LEDGER_HASH, "stage": "QUARANTINED",
        "quarantine_reason": "FAILED_OR_CANCELLED_NO_REPLAY",
        "native_inflight": 0, "run_id": None, "manual_dispatch": False,
        "original_sqlite_writes": 0, "github_writes": 0,
        "scientific_first_use": False,
        "recent_events": [
            {"kind": "ATTEMPT_QUARANTINED", "seq": 322},
            {"kind": "NATIVE_FAILED_PROVIDER_CUSTODY", "seq": 321},
            {"kind": "DISPATCH_POST_RETURNED", "seq": 320},
            {"kind": "BEFORE_DISPATCH_INTENT", "seq": 319},
            {"kind": "TASK_INTAKE", "seq": 318},
            {"kind": "NATIVE_DEVELOPMENT_ADMITTED", "seq": 317},
        ],
    }
    task = {"task_state": "Running", "same_original_task": True,
            "worker_run_completed_failure": True, "original_sqlite_writes": 0,
            "github_writes": 0, "task_changes": 0}
    def raw(e, t):
        return ("2026-10-29T12:05:28Z " +
                "F139_I1138_ORIGINAL_OWNER_POSTFAIL_CUSTODY=" +
                json.dumps(e,sort_keys=True,separators=(",",":")) + "\n" +
                "2026-10-29T12:05:28Z " +
                "F139_I1138_ORIGINAL_OWNER_TASK_READONLY=" +
                json.dumps(t,sort_keys=True,separators=(",",":")) + "\n").encode()
    return evidence, task, raw


def run_fixture(*, original):
    if original:
        return {"id":g.OWNER_RUN,"head_sha":g.OWNER_HEAD,
                "head_branch":"qualification/f139-v19-i1138-postfailed-custody-ro-20261029",
                "event":"push","run_attempt":1,"status":"completed",
                "conclusion":"success",
                "actor":{"login":"spoonman136668-ai"},
                "repository":{"full_name":"spoonman136668-ai/FORGE"},
                "head_repository":{"full_name":"spoonman136668-ai/FORGE"}}
    return {"id":g.PROVIDER_RUN,"head_sha":g.OWNER_SOURCE,
            "head_branch":"f139-owner-release-"+g.OWNER_SOURCE,
            "event":"workflow_dispatch","run_attempt":1,"status":"completed",
            "conclusion":"failure",
            "actor":{"login":"spoonman136668-ai"},
            "repository":{"full_name":"spoonman136668-ai/FORGE"},
            "head_repository":{"full_name":"spoonman136668-ai/FORGE"}}


class OriginalCustodyTests(unittest.TestCase):
    def test_original_owner_log_is_historical_negative_not_live_signer(self):
        e,t,raw=owner_fixture()
        witness=g.owner_log_extract(raw(e,t))
        self.assertEqual(witness["head_seq"],322)
        self.assertEqual(witness["stage"],"QUARANTINED")
        self.assertIs(witness["real_owner_HMAC_verified_by_this_gate"],False)
        self.assertIs(witness["contemporaneous_process_running_verified"],False)

    def test_owner_no_replay_negative_matrix(self):
        changes=[
            ("stage","VERIFIED"),("head_seq",323),("run_id",g.PROVIDER_RUN),
            ("quarantine_reason","RETRIED"),("native_inflight",1),
            ("manual_dispatch",True),("original_sqlite_writes",1),
            ("github_writes",1),("scientific_first_use",True),
            ("head_sha256","f"*64),("ticket","another"),
        ]
        e,t,raw=owner_fixture()
        for key,value in changes:
            copied=copy.deepcopy(e);copied[key]=value
            with self.subTest(key=key),self.assertRaises(g.G34Denied):
                g.owner_log_extract(raw(copied,t))

    def test_original_owner_event_sequence_and_task_drift(self):
        e,t,raw=owner_fixture()
        altered=copy.deepcopy(e)
        altered["recent_events"][0]["kind"]="PROVIDER_VERIFIED_TERMINAL"
        with self.assertRaises(g.G34Denied):
            g.owner_log_extract(raw(altered,t))
        for key,value in [("task_state","Ready"),
                          ("same_original_task",False),
                          ("worker_run_completed_failure",False),
                          ("task_changes",1)]:
            b=dict(t);b[key]=value
            with self.subTest(key=key),self.assertRaises(g.G34Denied):
                g.owner_log_extract(raw(e,b))

    def test_duplicate_or_missing_owner_log_markers_fail(self):
        e,t,raw=owner_fixture()
        old=raw(e,t)
        for changed in (old+old,old.split(b"\n")[0],
                        b"no original owner witness"):
            with self.assertRaises(g.G34Denied):
                g.owner_log_extract(changed)

    def test_original_failed_provider_run_cannot_be_reclassified(self):
        good=run_fixture(original=False)
        g.validate_run(good,run_id=g.PROVIDER_RUN,source=g.OWNER_SOURCE,
                       result="failure",event="workflow_dispatch",
                       branch="f139-owner-release-"+g.OWNER_SOURCE)
        for field,value in [
            ("conclusion","success"),("head_sha","0"*40),
            ("run_attempt",2),("event","push"),
            ("head_branch","main"),("id",g.PROVIDER_RUN+1)]:
            x=dict(good);x[field]=value
            with self.subTest(field=field),self.assertRaises(g.G34Denied):
                g.validate_run(x,run_id=g.PROVIDER_RUN,
                               source=g.OWNER_SOURCE,result="failure",
                               event="workflow_dispatch",
                               branch="f139-owner-release-"+g.OWNER_SOURCE)

    def test_original_owner_witness_run_source_is_separate(self):
        run=run_fixture(original=True)
        g.validate_run(run,run_id=g.OWNER_RUN,source=g.OWNER_HEAD,
                       result="success",event="push",
                       branch="qualification/f139-v19-i1138-postfailed-custody-ro-20261029")
        run["head_sha"]=g.OWNER_SOURCE
        with self.assertRaises(g.G34Denied):
            g.validate_run(run,run_id=g.OWNER_RUN,source=g.OWNER_HEAD,
                           result="success",event="push",
                           branch="qualification/f139-v19-i1138-postfailed-custody-ro-20261029")

    def test_json_repeated_keys_and_untrusted_body_denied(self):
        for body in (b'{"x":1,"x":2}',b'[]',b'null',b'{incomplete',
                     b'',b'{"a":"\\uD800"}'):
            with self.subTest(body=body),self.assertRaises(
                (g.G34Denied,UnicodeError)
            ):
                g.json_obj(body,"UNTRUSTED")

    def test_missing_and_swapped_provider_artifacts_rejected(self):
        for chunks in [
            {"artifacts":[],"total_count":0},
            {"artifacts":[{"id":g.EXPECTED["ubuntu-latest"]["id"]}],
             "total_count":1},
        ]:
            with self.assertRaises(g.G34Denied):
                g.provider_artifacts(json.dumps(chunks).encode(),
                                     {"ubuntu-latest":b"x",
                                      "windows-latest":b"x"})


if __name__=="__main__":
    unittest.main()
