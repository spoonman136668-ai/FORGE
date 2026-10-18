"""F124-AX independent frozen-source, equal public cost, and model-bound focused tests.

No new scientific candidate election, held SCREEN, or DEV is constructed here.
Tests use synthetic PUBLIC demonstrations and do not read AW consumed DEV.
"""
import inspect
import unittest
import f124ax_train_source as source
import f124ax_nonlinear_public_inverse as model
import f124ax_fit_screen as screen
import f124av_informative_inverse as original

class TestF124AX(unittest.TestCase):
    def test_identity_and_new_source_split(self):
        doc=source.frozen()
        self.assertEqual(source.witness.blob(source.FREEZE),source.FREEZE_BLOB)
        self.assertEqual(doc["lineage"]["qualified_AW_parent"],source.PARENT_HEAD)
        self.assertEqual(doc["source"]["total_public_responses_per_task"],48)
        self.assertEqual(len(doc["Yggdrasil"]["models"]),6)
        self.assertEqual(len(screen.SPECS),6)
        self.assertTrue(set(source.OPERATORS["TRAIN"]).isdisjoint(
            source.OPERATORS["DEV"]))
        with self.assertRaises(Exception):
            source.build(source.COHORTS["Yggdrasil"]["DEV"].start,source.VECTORS[0],"DEV")
        with self.assertRaises(Exception):
            source.rows("DEV")

    def test_original_pair_and_public_query_budget(self):
        seed=source.COHORTS["Yggdrasil"]["TRAIN"].start
        vec=source.VECTORS[0]
        fam,op,nonce,p,n,_=source.build(seed,vec)
        self.assertEqual(p["demos"],n["demos"])
        self.assertEqual(len(p["demos"]),24)
        balanced=source.public48(seed,vec,op,"balanced_basis48",p["demos"])
        random=source.public48(seed,vec,op,"random48",p["demos"])
        self.assertEqual(len(balanced),len(random))
        self.assertEqual(len(balanced),48)
        self.assertEqual(balanced[:24],random[:24])
        self.assertNotEqual(balanced[24:],random[24:])
        for rows in (balanced,random):
            self.assertEqual(sum(source.relation(
                d["input_bits"],op)!=d["output_bits"] for d in rows),6)

    def test_models_use_public_only(self):
        for mod in (model,):
            code=inspect.getsource(mod)
            self.assertNotIn("import f124ax_train_source",code)
            self.assertNotIn("import f124av_train_source",code)
            self.assertNotIn("source.plain(",code)
        demos=[]
        for idx in range(48):
            x=[(idx>>k)&1 for k in range(6)]+[int((idx+k)%2==0) for k in range(10)]
            y=[x[(k+3)%16]^(x[k]&x[(k+1)%16]) for k in range(16)]
            demos.append({"output_bits":x,"input_bits":y})
        for mode in model.MODES:
            fit=model.train(demos,mode)
            self.assertFalse(fit["operator_catalog_used"])
            self.assertFalse(fit["model_family_known"])
            self.assertGreater(fit["extra_model_bits_lower"],0)
            self.assertEqual(len(model.predict(fit,demos[40]["output_bits"])),16)
            correct=model.public_check(fit,demos)
            self.assertTrue(0<=correct<=128)
        with self.assertRaises(Exception):
            model.train(demos[:47],model.MODES[0])
        with self.assertRaises(Exception):
            model.train(demos,"non_preregistered_mode")
        self.assertEqual(original.FIT,40)
        self.assertEqual(original.TOTAL,48)
        self.assertEqual(original.TRIALS,256)

    def test_fit_lock_before_screen(self):
        d={k:screen.blank() for k,_,_ in screen.SPECS}
        for v in d.values():v["FP"]=0;v["paired"]=0
        self.assertIsNone(screen.choose(d))
        d["quadratic_public_inverse_basis48"]["paired"]=3
        d["nearest_public_inverse_random48"]["paired"]=2
        self.assertEqual(screen.choose(d),"quadratic_public_inverse_basis48")
        d["quadratic_public_inverse_basis48"]["FP"]=1
        self.assertEqual(screen.choose(d),"nearest_public_inverse_random48")

if __name__=="__main__":unittest.main()
