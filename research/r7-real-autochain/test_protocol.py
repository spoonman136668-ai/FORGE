import copy,json,pathlib,sys,unittest
HERE=pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import protocol,review

class FrozenGate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw=(HERE/"frozen.json").read_bytes()
        cls.manifest=protocol.protocol(cls.raw)
        cls.head="a"*40
        cls.run_id="987654321"
        cls.claim_obj={"schema":"forge.r7.firstuse-budget-consumed.v1",
          "branch":"research/forge-r7-real-autochain-firstuse",
          "experiment_ids":list(protocol.STAGES),"first_uses_consumed":2,
          "reruns_allowed":False,"source_manifest_sha256":protocol.digest(cls.raw),
          "run_id":cls.run_id,"head_sha":cls.head,
          "external_fsa_activated":False,"independent_custody_qualified":False,
          "scientific_accepted":False,"paid_api_calls":0}
    def encode(self,x):return (json.dumps(x,sort_keys=True)+"\n").encode()
    def parent(self,stage=0):
        if stage==0:return {"schema":"forge.r35.independent-original-review.v1",
          "experiment_id":protocol.PARENT,"outcome":"NO_CONFIRMED_QUARTILE_GAIN",
          "original_replay_allowed":False,"independently_validated":True,"science_production_accepted":False}
        return {"schema":"forge.r7.independent-development-review.v1",
          "experiment_id":protocol.STAGES[0],"stage_index":0,"outcome":"NO_CONFIRMED_QUARTILE_GAIN",
          "original_replay_allowed":False,"independently_validated":True,"science_production_accepted":False}
    def original(self,stage=0):
        meta=self.manifest["stages"][stage];parent=self.encode(self.parent(stage))
        arms={}
        for block in range(1,4):
            one={}
            for arm in ("control","candidate"):
                rows=[{"seed":seed,"correct":54.0,"total":108,
                       "family_correct":{"A":18.0,"B":18.0,"C":18.0}}
                      for seed in meta["sealed_heldout_seeds"]]
                one[arm]={"by_seed":rows,"accuracy":0.5,
                          "family_accuracy":{"A":0.5,"B":0.5,"C":0.5},
                          "source_training_example_counts":{"A":576,"B":576,"C":576},
                          "weights_sha256":"b"*64}
            arms[str(block)]=one
        model={"schema":"forge.r35.quartile-original.v1",
          "method_source_sha":protocol.WING_SHA,"model_calls":0,
          "science_production_accepted":False,"candidate_mode":"quartile025",
          "parent_r34_experiment_id":meta["parent_experiment_id"],
          "parent_review_outcome":self.parent(stage)["outcome"],
          "development_blocks":meta["development_blocks"],
          "sealed_heldout_seeds":meta["sealed_heldout_seeds"],
          "results":arms,"comparisons":[{"block":i,"strict":False,"partial":False,
             "worst_family_gain":0.0,"candidate_accuracy":0.5,
             "family_deltas":{"A":0.0,"B":0.0,"C":0.0}} for i in range(1,4)],
          "classification":"NO_CONFIRMED_QUARTILE_GAIN"}
        obj={"schema":"forge.r7.real-wingless-development-original.v1",
          "experiment_id":protocol.STAGES[stage],"stage_index":stage,
          "parent_experiment_id":meta["parent_experiment_id"],
          "parent_outcome":self.parent(stage)["outcome"],
          "parent_review_sha256":protocol.digest(parent),
          "frozen_manifest_sha256":protocol.digest(self.raw),
          "method_legacy_git_blob":protocol.LEGACY_BLOB,
          "wingless_source_commit":protocol.WING_SHA,
          "run_id":self.run_id,"launch_head_sha":self.head,
          "firstuse_budget_consumed_before_compute":True,
          "original_replay_allowed":False,"scientific_accepted":False,
          "paid_api_calls":0,"scientific_development_result":model,
          "outcome":"NO_CONFIRMED_QUARTILE_GAIN"}
        return obj
    def v(self,orig,stage=0):
        return review.verify(self.raw,self.encode(orig),self.encode(self.parent(stage)),
          self.encode(self.claim_obj),stage,self.run_id,self.head)
    def test_two_independent_frozen_stage_reviews(self):
        for stage in (0,1):
            result=self.v(self.original(stage),stage)
            self.assertTrue(result["independently_validated"])
            self.assertFalse(result["external_fsa_qualified"])
            self.assertFalse(result["next_science_dispatch_authorized"])
            self.assertEqual(result["outcome"],"NO_CONFIRMED_QUARTILE_GAIN")
    def test_duplicate_or_tampered_manifest(self):
        with self.assertRaises(ValueError):protocol.protocol(self.raw.replace(b'"max_real_originals": 2',b'"max_real_originals": 3'))
        with self.assertRaises(ValueError):protocol.load(b'{"stage":0,"stage":1}')
        x=copy.deepcopy(self.manifest);x["stages"][1]["sealed_heldout_seeds"][0]=18200
        with self.assertRaises(ValueError):protocol.protocol(self.encode(x))
    def test_wrong_firstuse_claim_and_replay(self):
        x=copy.deepcopy(self.claim_obj);x["first_uses_consumed"]=0
        with self.assertRaises(ValueError):
            protocol.claim_ok(self.encode(x),self.raw,0,self.run_id,self.head)
        x=copy.deepcopy(self.claim_obj);x["reruns_allowed"]=True
        with self.assertRaises(ValueError):
            protocol.claim_ok(self.encode(x),self.raw,0,self.run_id,self.head)
    def test_row_edit_cannot_flip_outcome(self):
        original=self.original(0)
        original["scientific_development_result"]["results"]["2"]["candidate"]["by_seed"][0]["correct"]=108.0
        with self.assertRaises(ValueError):self.v(original)
    def test_one_lane_parent_does_not_authorize_another(self):
        original=self.original(1)
        original["parent_experiment_id"]=protocol.PARENT
        with self.assertRaises(ValueError):self.v(original,1)
    def test_no_future_stage_backdating(self):
        m=self.manifest
        a=set(sum(m["stages"][0]["development_blocks"],[])+m["stages"][0]["sealed_heldout_seeds"])
        b=set(sum(m["stages"][1]["development_blocks"],[])+m["stages"][1]["sealed_heldout_seeds"])
        self.assertFalse(a&b)
        self.assertEqual(len(a),96)
        self.assertEqual(len(b),96)
if __name__=="__main__":unittest.main()
