import copy,json,pathlib,sys,unittest
HERE=pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import protocol,controller
class FrozenR11(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw=(HERE/"frozen.json").read_bytes()
        cls.plan=protocol.freeze(cls.raw)
    def encode(self,obj):return (json.dumps(obj,sort_keys=True)+"\n").encode()
    def test_parent_real_R10_failure_pinned(self):
        self.assertEqual(self.plan["parent"]["sha256"],protocol.PIN)
        self.assertEqual(self.plan["parent"]["artifact_id"],11939807429)
        self.assertFalse(any(x["development_gate_passed"] for x in self.plan["parent"]["frozen_outcomes"]))
        self.assertEqual(self.plan["authority"]["new_scientific_originals"],0)
    def test_true_new_seed_cohort_and_retention(self):
        d=self.plan["development"]
        seeds=sum(d["train_blocks"],[])+d["reserved_future_sealed_seeds"]+sum(d["reserved_future_replication_training"],[])+d["reserved_future_replication_sealed"]
        self.assertEqual(len(seeds),192)
        self.assertEqual(len(set(seeds)),192)
        self.assertTrue(all(x>=28000 for x in seeds))
        self.assertEqual(self.plan["method"]["persistent_memory_slots_per_source"]*3,96)
        self.assertEqual(self.plan["method"]["epochs"],32)
        self.assertFalse(self.plan["method"]["no_validation_feedback_to_memory"] is False)
    def test_invalid_prior_reclassification_and_claim_rejected(self):
        f=copy.deepcopy(self.plan);f["parent"]["frozen_outcomes"][0]["development_gate_passed"]=True
        with self.assertRaises(ValueError):protocol.freeze(self.encode(f))
        f=copy.deepcopy(self.plan);f["authority"]["first_use_claims"]=1
        with self.assertRaises(ValueError):protocol.freeze(self.encode(f))
        f=copy.deepcopy(self.plan);f["method"]["controller_lr"]=5.0
        with self.assertRaises(ValueError):protocol.freeze(self.encode(f))
        f=copy.deepcopy(self.plan);f["development"]["train_blocks"][0][0]=28200
        with self.assertRaises(ValueError):protocol.freeze(self.encode(f))
    def test_duplicate_json_and_false_parent_rejected(self):
        with self.assertRaises(ValueError):protocol.parse(b'{"first_use":0,"first_use":1}')
        fake={"schema":"forge.r10.independent-two-method-real-development-review.v1",
             "prospective_method_proposal":None,"scientific_accepted":False,
             "new_scientific_first_use_authorized":False,"method_superiority_established":False,
             "sealed_cohort_accessed":False,"originals_executed":0,
             "ranked_heldout_blind_development_candidates":[{"id":"W36-C4","mean_min_family_gain":0.018229166666666685,"development_gate_passed":False},
              {"id":"W36-C2","mean_min_family_gain":-0.052662037037037035,"development_gate_passed":False}]}
        with self.assertRaises(ValueError):protocol.verify_parent(self.encode(fake),self.plan)
    def test_retention_controller_reconstructible_on_small_synthetic_source(self):
        # A *synthetic unit fixture*, not a scientific original or proof of gain.
        groups=[]
        for s in range(3):
            rows=[]
            for i in range(576):
                x=[0.0]*16
                x[(i+s)%16]=1 if i%2==0 else -1
                rows.append((tuple(x),1 if i%2==0 else -1))
            groups.append(rows)
        a=controller.train(groups);b=controller.train(groups)
        self.assertEqual(a,b)
        self.assertEqual(a["persistent_memory_slots"],96)
        self.assertEqual(a["learned_controller_parameters"],3)
        self.assertEqual(len(a["gate_trace"]),32)
        self.assertEqual(len(a["weights"]),16)
        self.assertEqual(len(a["gate_logits"]),3)
        for epoch in a["gate_trace"]:
            self.assertEqual(len(epoch["sources"]),3)
            for source in epoch["sources"]:
                self.assertEqual(source["retained_slots"],32)
                self.assertTrue(0<=source["hard_slots_requested"]<=32)
                self.assertTrue(112<=source["proxy_count"]<=118)
if __name__=="__main__":unittest.main()
