"""K4D prospective invariants, source-only with no PyBullet import."""
import copy
import hashlib
import json
import unittest

import numpy as np

from k4d_crossfamily import FROZEN, frozen_cases, varied_target
from k4c_intervention_pair import PairFailure
from k4d_compare_processes import compare


def sample_reports():
    frozen=json.loads(FROZEN.read_text(encoding="utf-8"))
    entries=[
        {"case":c,"status":"PASS","first_physical_effect_step":0,
         "control_sha256":"a"*64,"treated_sha256":"b"*64,
         "restoration_exact":True,"uncontaminated":True}
        for c in frozen_cases(frozen)
    ]
    record={"schema":"mass.lcrm01.k4d.paired-crossfamily-development-result.v1",
            "gate":"LCRM01-K4D",
            "result":"PASS_ALL_EIGHT",
            "causalworld_commit":frozen["baseline"]["source_commit"],
            "protocol_sha256":hashlib.sha256(FROZEN.read_bytes()).hexdigest(),
            "cases":entries,"scientific_first_use":False,
            "learned_transfer":False,"scientific_accepted":False,
            "dispatch_authorized":False,"prior_negative_preserved":True}
    return record,copy.deepcopy(record)


class K4DSourceOnly(unittest.TestCase):
    def test_frozen_eight_cases_distinct(self):
        cases=frozen_cases(json.loads(FROZEN.read_text()))
        self.assertEqual(len(cases),8)
        self.assertEqual(set(x["task"] for x in cases),{"pushing","reaching"})
        self.assertEqual(set(x["seed"] for x in cases),{41,53})
        self.assertEqual(set(x["joint_index"] for x in cases),{0,2})

    def test_signed_single_joint_targets_are_unclipped(self):
        joints=np.zeros(9)
        bounds=np.stack([np.full(9,-1.),np.full(9,1.)])
        for index,delta in ((0,.04),(2,-.03)):
            target=varied_target(np,joints,bounds,index,delta)
            self.assertAlmostEqual(target[index],delta)
            self.assertEqual(np.count_nonzero(target),1)

    def test_unrealizable_intervention_denied(self):
        joints=np.zeros(9)
        joints[2]=-.99
        bounds=np.stack([np.full(9,-1.),np.full(9,1.)])
        with self.assertRaises(PairFailure):
            varied_target(np,joints,bounds,2,-.03)

    def test_hidden_or_extra_intervention_denied(self):
        joints=np.zeros(9)
        bounds=np.stack([np.full(9,-1.),np.full(9,1.)])
        for index,delta in ((0,.02),(1,.04),(2,.04),(0,-.03)):
            with self.subTest(index=index,delta=delta):
                with self.assertRaises(PairFailure):
                    varied_target(np,joints,bounds,index,delta)

    def test_cross_process_exact_success(self):
        a,b=sample_reports()
        report=compare(a,b,hashlib.sha256(FROZEN.read_bytes()).hexdigest())
        self.assertEqual(report["result"],"PASS")
        self.assertFalse(report["scientific_accepted"])

    def test_changed_process_digest_denied(self):
        a,b=sample_reports()
        b["cases"][3]["treated_sha256"]="c"*64
        report=compare(a,b,a["protocol_sha256"])
        self.assertEqual(report["result"],"NOT_QUALIFIED")
        self.assertEqual(report["mismatches"][0]["index"],3)
        self.assertIn("treated_sha256",report["mismatches"][0]["differing_fields"])

    def test_negative_is_preserved_not_promoted(self):
        a,b=sample_reports()
        for x in (a,b):
            x["result"]="NEGATIVE_RETAINED"
            x["cases"][0]={"case":x["cases"][0]["case"],"status":"NEGATIVE",
                            "first_failure":{"phase":"RESTORE","step":-1,
                                             "fields":["numpy_rng"]}}
        report=compare(a,b,a["protocol_sha256"])
        self.assertEqual(report["result"],"NOT_QUALIFIED")
        self.assertTrue(report["matching_reports"])

    def test_source_identity_mismatch_denied(self):
        a,b=sample_reports()
        b["causalworld_commit"]="e"*40
        with self.assertRaises(ValueError):
            compare(a,b,a["protocol_sha256"])

    def test_false_authority_denied(self):
        a,b=sample_reports()
        a["scientific_first_use"]=True
        with self.assertRaises(ValueError):
            compare(a,b,a["protocol_sha256"])

    def test_missing_case_denied(self):
        a,b=sample_reports()
        b["cases"].pop()
        with self.assertRaises(ValueError):
            compare(a,b,a["protocol_sha256"])

if __name__=="__main__":
    unittest.main()
