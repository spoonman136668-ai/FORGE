import copy,json,pathlib,sys,unittest
HERE=pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import protocol,model,review
class R12Contract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw=(HERE/"frozen.json").read_bytes()
        cls.plan=protocol.manifest(cls.raw)
    def test_training_never_sees_future_or_reserved_graphs(self):
        seeds=self.plan["seeds"]
        self.assertFalse(set(seeds["train"]) & set(seeds["development"]+seeds["structural_stress"]+seeds["reserved_sealed"]))
        self.assertEqual(len(seeds["reserved_sealed"]),32)
        self.assertEqual(self.plan["authority"]["first_use_claims"],0)
        self.assertEqual(self.plan["encoder"]["learnable_scalar_count"],8)
    def test_generator_and_independent_reviewer_match_on_unseen_structures(self):
        weights=self.plan["encoder"]["initial_weights"]
        for seed,hops in ((30003,4),(32007,6)):
            graph,queries=model.build(seed,hops)
            independent,cases=review.graph_case(seed,hops)
            self.assertEqual([(s[0],s[1],s[2:]) for s in graph],
                             [(s["src"],s["dst"],s["rel"]) for s in independent])
            self.assertEqual([(s,list(roles),target) for s,roles,target in queries],
                             [(x["start"],x["roles"],x["target"]) for x in cases])
            for (start,roles,target),question in zip(queries,cases):
                for name in model.FIELDS:
                    a=model.raw(graph,start,roles) if name=="chronological_raw" else model.compressed(graph,start,roles,name,weights)
                    b=review.reply(independent,question,weights,name)
                    self.assertEqual(a,b)
            self.assertLessEqual(len(graph),16)
    def test_query_blind_encoder_and_untouched_sealed_source(self):
        graph,qs=model.build(31000,4)
        self.assertEqual(len(graph),16)
        self.assertEqual(len(qs),4)
        code=model.embed((0,2),self.plan["encoder"]["initial_weights"])
        self.assertEqual(code,model.embed((0,2),self.plan["encoder"]["initial_weights"]))
        self.assertEqual(model.score(graph,qs,self.plan["encoder"]["initial_weights"],"exact_pair")[0],4)
        self.assertEqual(len(model.build(32000,6)[0]),15)
    def test_source_and_decision_mutations_denied(self):
        plan=copy.deepcopy(self.plan)
        plan["authority"]["scientific_accepted"]=True
        with self.assertRaises(protocol.Blocked):protocol.manifest(json.dumps(plan).encode())
        plan=copy.deepcopy(self.plan)
        plan["seeds"]["reserved_sealed"][0]=30000
        with self.assertRaises(protocol.Blocked):protocol.manifest(json.dumps(plan).encode())
        plan=copy.deepcopy(self.plan)
        plan["decision"]["minimum_stress_gain_vs_fixed_hash"]=0.0
        with self.assertRaises(protocol.Blocked):protocol.manifest(json.dumps(plan).encode())
    def test_row_measurement_cap_is_separate_from_frozen_source_cap(self):
        # Real per-query evidence is larger than a frozen prereg. It must be
        # admissible to the independent auditor, but not as a frozen manifest.
        payload=b'{"rows":"' + b"x"*45000 + b'"}'
        with self.assertRaises(protocol.Blocked):protocol.parse(payload)
        self.assertEqual(len(protocol.parse(payload,cap=600000)["rows"]),45000)
        with self.assertRaises(protocol.Blocked):protocol.parse(b'{}',cap=600001)
    def test_duplicate_keys_or_bad_science_denied(self):
        with self.assertRaises(protocol.Blocked):protocol.parse(b'{"a":1,"a":2}')
        with self.assertRaises(protocol.Blocked):protocol.parse(b'{"a":NaN}')
        with self.assertRaises(protocol.Blocked):
            protocol.parent(json.dumps({"schema":"forge.r11.independent-learned-retention-development.v1"}).encode(),self.plan)
    def test_training_objective_only_training(self):
        w=self.plan["encoder"]["initial_weights"]
        n,k=model.training_objective(w,self.plan["seeds"]["train"][:2])
        self.assertEqual(k,14)
        self.assertGreaterEqual(n,0)
        self.assertLessEqual(n,k)
        nr,kr=review.train_count(w,self.plan["seeds"]["train"][:2])
        self.assertEqual((n,k),(nr,kr))
if __name__=="__main__":unittest.main()
