"""F124CN source-free adversarial learning tests. No original births/evaluation."""
import json, pathlib, random, subprocess, sys, unittest
import learn

def artificial_fit(k0=7,salt=1):
    xs=random.Random(81144+salt+k0).sample(range(65536),300)
    def out0(x):
        a,b,c,t=learn.nibbles(x)
        return ((b if (t^salt)&1 else a)+5*c+3*t+k0)&15
    train=[(x,out0(x)^(1 if i in (1,5,12,19,24,35) else 0))
           for i,x in enumerate(xs[:40])]
    return train,[(x,out0(x)) for x in xs[40:]]

class PublicOnlyMechanism(unittest.TestCase):
    def test_01_fits_actual_interactions_and_predicts_unseen_inputs(self):
        for k0 in (0,3,7,11):
            for salt in (0,1):
                fit,test=artificial_fit(k0,salt)
                m,log=learn.train(fit)
                self.assertEqual(m,(salt,5,3,k0))
                self.assertEqual(log["fit_errors"],6)
                self.assertTrue(all(learn.predict(m,x)==y for x,y in test))
                self.assertEqual(log["row_scans"],5120)
    def test_02_separate_matched_conventional_exhaustive_ties(self):
        fit,test=artificial_fit()
        a,_=learn.train(fit)
        b,trace=learn.conventional_four_parent(fit)
        self.assertEqual(a,b)
        self.assertEqual(trace["fit_errors"],6)
        self.assertEqual(trace["row_scans"],81920)
    def test_03_weak_two_parent_bounded_and_source_public(self):
        fit,test=artificial_fit()
        m,trace=learn.conventional_two_parent(fit)
        self.assertLessEqual(trace["fit_errors"],40)
        self.assertTrue(all(0<=learn.predict_two(m,x)<16 for x,y in test))
        self.assertEqual(trace["row_scans"],19440)
    def test_04_no_context_is_not_expressively_equivalent(self):
        fit,test=artificial_fit()
        ablation=learn.ablation(fit)
        self.assertGreater(sum(learn.predict_ablation(ablation,x)!=y
                               for x,y in test),0)
    def test_05_true_new_process_checkpoint_preserves_learned_actions(self):
        fit,test=artificial_fit()
        model,_=learn.train(fit)
        blob=learn.snapshot(model)
        code=("import sys,json,learn; m=learn.restore(sys.stdin.buffer.read());"
              "print(json.dumps({'y':learn.predict(m,int(sys.argv[1])),"
              "'snapshot':learn.snapshot(m).decode()}))")
        cmd=[sys.executable,"-B","-c",code,str(test[0][0])]
        for _ in range(2):
            p=subprocess.run(cmd,input=blob,cwd=pathlib.Path(__file__).parent,
                             capture_output=True,timeout=20,check=True)
            data=json.loads(p.stdout)
            self.assertEqual(data["y"],test[0][1])
            self.assertEqual(data["snapshot"],blob.decode())
    def test_06_reject_recomputed_checksum_with_false_science_authority(self):
        model,_=learn.train(artificial_fit()[0])
        original=json.loads(learn.snapshot(model))
        for field,value in (("science_accepted",True),("source_executed",True),
                            ("source_secret","not-public"),("schema","REAL_SOURCE")):
            body=dict(original["body"]);body[field]=value
            fake=learn.canonical({"body":body,"sha256":
                                  __import__("hashlib").sha256(learn.canonical(body)).hexdigest()})
            with self.assertRaises(ValueError):learn.restore(fake)
    def test_07_tampered_and_duplicate_checkpoint_denied(self):
        raw=learn.snapshot(learn.train(artificial_fit()[0])[0])
        with self.assertRaises(ValueError):learn.restore(raw.replace(b"source_executed",b"sourcE_executed"))
        with self.assertRaises(ValueError):learn.restore(b'{"body":{},"body":{},"sha256":"x"}')
        with self.assertRaises(ValueError):learn.restore(raw+b"x")
    def test_08_frozen_input_role_and_domain(self):
        fit,_=artificial_fit()
        with self.assertRaises(ValueError):learn.train(fit[:-1])
        with self.assertRaises(ValueError):learn.train(fit[:-1]+fit[:1])
        for invalid in (True,-1,65536,"12"):
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError):learn.nibbles(invalid)
    def test_09_model_parameter_domains_fail_closed(self):
        for invalid in ((True,5,3,7),(0,0,3,7),(0,5,2,7),(0,5,3,16)):
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError):learn.snapshot(invalid)
    def test_10_learning_module_no_original_source_access(self):
        data=pathlib.Path(learn.__file__).read_text()
        self.assertNotIn("f124cj_internal_source",data)
        self.assertNotIn("source.task(",data)
        self.assertNotIn("private_source_param",data)
        self.assertNotIn("original_protected",data)

if __name__=="__main__":
    unittest.main()
