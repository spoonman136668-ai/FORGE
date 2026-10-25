"""F124CO learned-structure engineering tests: authored PUBLIC mathematical data only."""
import hashlib
import json
import pathlib
import random
import subprocess
import sys
import unittest

import learn_structure as s

def public_fit(model,seed):
    xs=random.Random(seed).sample(range(65536),304)
    ys=[s.result_from_public(model,x) for x in xs]
    fit=[(x,y^(1 if i in (1,5,12,19,24,35) else 0))
         for i,(x,y) in enumerate(zip(xs[:40],ys[:40]))]
    return fit,list(zip(xs[40:48],ys[40:48])),list(zip(xs[48:],ys[48:]))

class LearnedStructureTests(unittest.TestCase):
    def test_01_learn_source_free_e2_like_structure_from_public_fit(self):
        for bias in (2,6,10,14):
            for phase in (0,1):
                true=(0,1,3,phase,5,3,bias)
                fit,check,dev=public_fit(true,882000+7*bias+phase)
                learned,diag=s.train(fit)
                self.assertGreaterEqual(sum(s.result_from_public(learned,x)==y
                                            for x,y in dev),243)
                self.assertEqual(diag["layout_candidates"],1944)
                self.assertEqual(diag["residual_row_evaluations"],77760)
                self.assertTrue(s.valid_structure(learned))
    def test_02_learns_other_carrier_and_gate_structure(self):
        alternatives=[(0,2,1,1,7,9,11),(1,3,0,0,5,11,4)]
        for n,truth in enumerate(alternatives):
            fit,check,dev=public_fit(truth,930011+n)
            candidate,diag=s.train(fit)
            correct=sum(s.result_from_public(candidate,x)==y for x,y in dev)
            self.assertGreaterEqual(correct,243)
            self.assertEqual(diag["FIT_nibble_mismatches"],6)
    def test_03_independent_direct_fitted_same_class_control(self):
        true=(0,2,1,1,7,9,11)
        fit,check,dev=public_fit(true,951002)
        native,info=s.train(fit)
        reference,diag=s.conventional_enumeration(fit)
        self.assertEqual(native,reference)
        self.assertEqual(diag["full_candidate_words"],31104)
        self.assertEqual(diag["FIT_row_evaluations"],1244160)
    def test_04_no_predictive_ability_without_public_training(self):
        invalid=[(-1,1,2,0,5,3,7),(0,0,2,0,5,3,7),
                 (0,1,0,0,5,3,7),(0,1,3,2,5,3,7),
                 (0,1,3,1,2,3,7),(0,1,3,1,5,2,7)]
        for value in invalid:
            with self.subTest(value=value):
                self.assertFalse(s.valid_structure(value))
                with self.assertRaises(ValueError):s.checkpoint(value)
    def test_05_fresh_interpreter_retains_learned_structure(self):
        fit,_,dev=public_fit((0,2,1,1,7,9,11),943111)
        model,_=s.train(fit)
        wire=s.checkpoint(model)
        expr=("import sys,json,learn_structure as s;"
              "m=s.restore(sys.stdin.buffer.read());"
              "print(json.dumps({'m':list(m),'y':s.result_from_public(m,int(sys.argv[1])),"
              "'cp':s.checkpoint(m).decode()}))")
        expected=s.result_from_public(model,dev[0][0])
        for _ in range(2):
            process=subprocess.run([sys.executable,"-B","-c",expr,str(dev[0][0])],
               input=wire,cwd=pathlib.Path(__file__).parent,
               capture_output=True,check=True,timeout=20)
            returned=json.loads(process.stdout)
            self.assertEqual(returned["y"],expected)
            self.assertEqual(returned["m"],list(model))
            self.assertEqual(returned["cp"],wire.decode())
    def test_06_recomputed_checksum_cannot_grant_science_permission(self):
        fit,_,_=public_fit((0,1,3,1,5,3,7),902100)
        model,_=s.train(fit)
        before=json.loads(s.checkpoint(model))
        for field,value in (("science_accepted",True),("protected_firstuse",True),
                            ("source_created",True),("hidden_oracle","NO"),
                            ("schema","source-owner.v1")):
            new=dict(before["body"]);new[field]=value
            bad=s.canonical({"body":new,
                 "sha256":hashlib.sha256(s.canonical(new)).hexdigest()})
            with self.subTest(field=field):
                with self.assertRaises(ValueError):s.restore(bad)
    def test_07_checkpoint_strict_integrity_and_duplicate_keys(self):
        fit,_,_=public_fit((0,1,3,1,5,3,7),902101)
        m,_=s.train(fit)
        cp=s.checkpoint(m)
        with self.assertRaises(ValueError):s.restore(cp.replace(b"science_accepted",b"Science_accepted"))
        with self.assertRaises(ValueError):s.restore(cp+b"X")
        with self.assertRaises(ValueError):s.restore(b'{"body":{},"body":{},"sha256":"x"}')
    def test_08_invalid_public_fit_shapes_are_denied(self):
        fit,_,_=public_fit((0,1,3,1,5,3,7),902102)
        for invalid in (fit[:39],fit[:39]+[fit[0]],
                        fit[:39]+[(True,1)],fit[:39]+[(65536,1)]):
            with self.subTest(kind=str(invalid[-1])):
                with self.assertRaises(ValueError):s.train(invalid)
        for invalid in (True,False,-1,65536,"99"):
            with self.subTest(value=invalid):
                with self.assertRaises(ValueError):s.public4(invalid)
    def test_09_no_source_family_or_oracle_import_in_learner(self):
        content=pathlib.Path(s.__file__).read_text()
        for illegal in ("f124cj_internal_source","source.forward(", "source.task(",
                        "private_source_param","source_birth","FAMILIES["):
            self.assertNotIn(illegal,content)
    def test_10_fixed_deterministic_train_reproducibility(self):
        fit,_,dev=public_fit((0,2,1,0,3,13,9),910200)
        x,log1=s.train(fit)
        y,log2=s.train(fit)
        self.assertEqual(x,y)
        self.assertEqual(log1,log2)
        self.assertEqual(s.checkpoint(x),s.checkpoint(y))
        self.assertTrue(all(0<=s.result_from_public(x,a)<16 for a,b in dev))

if __name__=="__main__":
    unittest.main()
