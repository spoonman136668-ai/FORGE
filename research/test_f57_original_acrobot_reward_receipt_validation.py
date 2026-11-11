"""F57 pure untrusted receipt analysis tests. NO Gymnasium and NO new seeds."""
import ast
import copy
import inspect
import math
import unittest

import f57_original_acrobot_reward_admission as a
import f57_original_acrobot_reward_receipt_validation as s

OBS=[1.,0.,1.,0.,0.,0.1]
SNAP="a"*64


def episode(seed,mode,steps,action=2):
    trace=[]
    for idx in range(steps):
        trace.append([list(OBS),action,-1.,list(OBS),idx==steps-1,False])
    return {"seed":seed,"mode":mode,"trace":trace,
            "model_snapshot_sha256":SNAP,"decision_ns":steps*15,
            "episode_wall_seconds":max(.01,steps*.01)}


def sample(*,candidate_better=True):
    arms={}
    for arm in a.ARMS:
        n=1 if arm=="quantile-supported" and candidate_better else 25
        action=0 if arm=="quantile-supported" and candidate_better else 2
        transfer=[episode(seed,"nips",n,action) for seed in a.PROPOSED_TRANSFER]
        retention=[episode(seed,"book",n,action) for seed in a.PROPOSED_RETENTION]
        arms[arm]={"transfer":transfer,"retention":retention,
                   "cold_transfer":copy.deepcopy(transfer),
                   "cold_retention":copy.deepcopy(retention)}
    return {"manifest_sha256":a.digest(a.frozen_proposal()),
            "source_commit":a.frozen_proposal()["independent_upstream_commit"],
            "original_acrobot_blob":a.frozen_proposal()["original_acrobot_blob"],
            "fit_sha256":a.OLD_FIT_SHA256,"trained_fqi_sha256":a.OLD_FQI_SHA256,
            "preparation_seconds_by_arm":{x:(0. if x=="momentum-rule" else 8.) for x in a.ARMS},
            "arms":arms}


class PureF57ReceiptGate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.synthetic_positive=sample()
        cls.synthetic_negative=sample(candidate_better=False)

    def test_positive_synthetic_thresholds_still_cannot_admit_science(self):
        r=s.assess_untrusted_evidence(self.synthetic_positive)
        self.assertEqual(r["disposition"],s.UNVERIFIED)
        self.assertEqual(r["strongest_conventional"],"momentum-rule")
        self.assertEqual(r["paired_strict_transfer_wins"],16)
        self.assertGreaterEqual(r["transfer_return_gain"],15)
        self.assertEqual(r["nominal_cold_episodes_checked"],168)
        self.assertEqual(r["nominal_scored_episodes_parsed"],168)
        self.assertTrue(r["untrusted_data_meets_numeric_thresholds"])
        self.assertEqual(sum(r["frozen_development_checks"].values()),7)
        self.assertFalse(r["scientific_accepted"])
        self.assertFalse(r["eligible_to_run_or_promote"])
        self.assertFalse(r["external_original_physics_authenticated"])
        self.assertFalse(r["fsa_signed_start_witness_verified"])
        self.assertFalse(r["global_first_use_ledger_verified"])
        self.assertFalse(r["fsa_monotonic_anchor_readback_verified"])

    def test_synthetic_null_preserved_as_no_numeric_gain(self):
        r=s.assess_untrusted_evidence(self.synthetic_negative)
        self.assertEqual(r["disposition"],s.UNVERIFIED)
        self.assertFalse(r["untrusted_data_meets_numeric_thresholds"])
        self.assertEqual(r["transfer_return_gain"],0)
        self.assertEqual(r["paired_strict_transfer_wins"],0)
        self.assertFalse(r["frozen_development_checks"]["mean_transfer_gain"])
        self.assertFalse(r["frozen_development_checks"]["paired_strict_seed_wins"])
        self.assertEqual(r["nominal_cold_episodes_checked"],168)

    def test_cold_reward_and_public_action_tamper_rejected(self):
        m=copy.deepcopy(self.synthetic_positive)
        m["arms"]["quantile-supported"]["cold_transfer"][0]["trace"][0][1]=1
        with self.assertRaisesRegex(ValueError,"COLD_REPLAY_MISMATCH"):
            s.assess_untrusted_evidence(m)
        m=copy.deepcopy(self.synthetic_positive)
        m["arms"]["quantile-supported"]["cold_transfer"][0]["trace"][0][2]=0.
        with self.assertRaisesRegex(ValueError,"COLD_REPLAY_MISMATCH"):
            s.assess_untrusted_evidence(m)
        m=copy.deepcopy(self.synthetic_positive)
        m["arms"]["quantile-supported"]["cold_transfer"][0]["model_snapshot_sha256"]="b"*64
        with self.assertRaisesRegex(ValueError,"COLD_REPLAY_MISMATCH"):
            s.assess_untrusted_evidence(m)

    def test_missing_duplicate_reordered_and_forbidden_episode_seeds(self):
        for mutant in ("missing","duplicate","reorder","consumed"):
            m=copy.deepcopy(self.synthetic_positive)
            seq=m["arms"]["momentum-rule"]["transfer"]
            if mutant=="missing": seq.pop()
            elif mutant=="duplicate": seq[1]["seed"]=seq[0]["seed"]
            elif mutant=="reorder": seq[0],seq[1]=seq[1],seq[0]
            else:seq[0]["seed"]=a.F51_TRANSFER[0]
            with self.subTest(mutant=mutant),self.assertRaises(ValueError):
                s.assess_untrusted_evidence(m)

    def test_return_deduced_from_steps_and_reward_cannot_be_forged(self):
        m=copy.deepcopy(self.synthetic_positive)
        m["arms"]["momentum-rule"]["transfer"][0]["return"]=2000.0
        result=s.assess_untrusted_evidence(m)
        self.assertEqual(result["arm_metrics"]["momentum-rule"]["transfer_mean_return"],-25.)
        self.assertNotIn("scientific_pass",result)
        self.assertEqual(result["disposition"],s.UNVERIFIED)
        bad=copy.deepcopy(self.synthetic_positive)
        bad["arms"]["momentum-rule"]["transfer"][0]["trace"][0][2]=-2.
        with self.assertRaisesRegex(ValueError,"REWARD_DOMAIN"):
            s.assess_untrusted_evidence(bad)

    def test_invalid_action_cost_source_and_budget_refused(self):
        for label in ("bad_action","nan","over_budget","cost_nan","bad_source","missing_control"):
            m=copy.deepcopy(self.synthetic_positive)
            if label=="bad_action":
                m["arms"]["quantile-supported"]["transfer"][0]["trace"][0][1]=9
            elif label=="nan":
                m["arms"]["quantile-supported"]["transfer"][0]["trace"][0][2]=float("nan")
            elif label=="over_budget":
                m["arms"]["quantile-supported"]["transfer"][0]["trace"]*=501
            elif label=="cost_nan":
                m["preparation_seconds_by_arm"]["frozen-fqi"]=float("nan")
            elif label=="bad_source":
                m["original_acrobot_blob"]="0"*40
            elif label=="missing_control":
                del m["arms"]["always-td"]
            with self.subTest(label=label),self.assertRaises(ValueError):
                s.assess_untrusted_evidence(m)

    def test_terminal_and_continuity_negative_controls(self):
        for label in ("both_terminal","unterminated","actions_after_end",
                      "discontinuous"):
            m=copy.deepcopy(self.synthetic_positive)
            ep=m["arms"]["momentum-rule"]["transfer"][0]
            if label=="both_terminal":ep["trace"][-1][5]=True
            elif label=="unterminated":ep["trace"][-1][4]=False
            elif label=="actions_after_end":ep["trace"][0][4]=True
            else:ep["trace"][1][0]=[-1.,0.,1.,0.,0.,0.1]
            with self.subTest(label=label),self.assertRaises(ValueError):
                s.assess_untrusted_evidence(m)

    def test_no_fake_authorization_flag_or_candidate_can_promote(self):
        for fake in ({"authorized":True},
                     {"fsa_signature_verified":True,
                      "original_terminal_signature":"fake"},
                     {"scientific_accepted":True,"force_science":True}):
            m=copy.deepcopy(self.synthetic_positive)
            m.update(fake)
            r=s.assess_untrusted_evidence(m)
            self.assertEqual(r["disposition"],s.UNVERIFIED)
            self.assertFalse(r["eligible_to_run_or_promote"])
            self.assertFalse(r["scientific_accepted"])
        with self.assertRaises(PermissionError):
            a.start_scientific_experiment(authorized=True)

    def test_deterministic_untrusted_report_digest_and_no_runtime_effects(self):
        r1=s.assess_untrusted_evidence(self.synthetic_positive)
        r2=s.assess_untrusted_evidence(self.synthetic_positive)
        self.assertEqual(r1,r2)
        self.assertEqual(r1["report_sha256"],a.digest({
            k:v for k,v in r1.items() if k!="report_sha256"}))
        tree=ast.parse(inspect.getsource(s))
        imports=set()
        calls=set()
        for node in ast.walk(tree):
            if isinstance(node,ast.Import):
                imports.update(a.name for a in node.names)
            elif isinstance(node,ast.ImportFrom):
                imports.add(node.module)
            elif isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute):
                calls.add(node.func.attr)
        self.assertEqual(imports,{"math","re","f57_original_acrobot_reward_admission"})
        self.assertFalse({"step","reset","make","evaluate","dispatch","run",
                          "start_scientific_experiment","CompareAndSwap"}&calls)
        self.assertFalse({"gymnasium","socket","requests","subprocess"}&imports)


if __name__=="__main__":
    unittest.main()
