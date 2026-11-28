"""L7 adversarial audits of exact E2E source identity, factual copying and controls."""
import os
from pathlib import Path
import unittest

from source import (
    FILES,ROLES,COUNTS,verify,load,parse_mr,identity,
    cohorts,canonical,digest,
)
from models import (
    PublicLanguageRealizer,LearnedPatterns,
    contains_value,delex,PLACEHOLDER
)
from runner import ARMS,guard,evaluate,token_f1


class L7MeaningToNaturalLanguage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        folder=os.environ.get("L7_RAW_CORPUS_DIRECTORY")
        if not folder:
            raise RuntimeError("L7_IMMUTABLE_E2E_CORPUS_NOT_STAGED")
        cls.raw={n:(Path(folder)/n).read_bytes() for n in FILES}
        cls.hashes,cls.roles=load(folder)

    def test_frozen_protocol_pins_unchanged_native_scientific_authorities(self):
        p=guard()
        self.assertEqual(tuple(p["arms"]),ARMS)
        self.assertEqual(p["cohorts"]["role_counts"],COUNTS)
        for key in ("Q21 successor","NCI-04","ITD-01","BIO",
                    "Mass Research","FORGE CKB-plane sole authority"):
            self.assertIn(key,p["governance"]["preserve"])

    def test_train_and_development_external_git_blobs_exact(self):
        for name in FILES:
            self.assertEqual(len(self.raw[name]),FILES[name][0])
            self.assertEqual(verify(self.raw[name],name),self.hashes[name])

    def test_one_byte_external_source_change_and_truncation_fail_closed(self):
        for name in FILES:
            bad=bytearray(self.raw[name])
            bad[35]^=1
            with self.assertRaisesRegex(ValueError,"GIT_BLOB_DRIFT"):
                verify(bytes(bad),name)
            with self.assertRaisesRegex(ValueError,"RAW_SIZE_DRIFT"):
                verify(self.raw[name][:-1],name)

    def test_actual_MR_parser_extracts_attributes_not_surface_oracles(self):
        mr=parse_mr("name[The Eagle], food[Italian], customer rating[3 out of 5]")
        self.assertEqual(mr["name"],"The Eagle")
        self.assertEqual(mr["food"],"Italian")
        self.assertEqual(mr["customerrating"],"3 out of 5")
        with self.assertRaises(ValueError):
            parse_mr("name[Two], name[Three]")
        with self.assertRaises(ValueError):
            parse_mr("name[Two] unrelated text")

    def test_three_immutable_different_meaning_role_cohorts(self):
        known=set()
        for role in ROLES:
            rows=self.roles[role]
            self.assertEqual(len(rows),COUNTS[role])
            for row in rows:
                key=identity(row["mr"])
                self.assertNotIn(key,known)
                known.add(key)
                self.assertTrue(row["ref"])
                self.assertTrue(row["mr"])
            self.assertEqual(len(digest(rows)),64)

    def test_role_identity_reconstruction_is_same_source(self):
        regenerated=cohorts(self.raw["trainset.csv"],self.raw["devset.csv"])
        self.assertEqual(
            {role:digest(v) for role,v in regenerated.items()},
            {role:digest(v) for role,v in self.roles.items()}
        )

    def test_train_pattern_delex_only_uses_visible_meaning_values(self):
        sample="The Eagle serves Italian food and is near Burger King."
        mr={"name":"The Eagle","food":"Italian","near":"Burger King"}
        templ=delex(sample,mr)
        self.assertIn("{{name}}",templ)
        self.assertIn("{{food}}",templ)
        self.assertIn("{{near}}",templ)
        out=LearnedPatterns.render(templ,mr)
        self.assertEqual(out,sample)

    def test_independent_retrieval_is_fitted_not_test_source_reference(self):
        fit=self.roles["L7_TRAIN"][:50]
        unseen=self.roles["L7_DEV"][0]
        model=PublicLanguageRealizer("REFERENCE_RETRIEVAL",fit)
        original=model.checkpoint()
        got,work=model.generate(unseen["mr"])
        self.assertTrue(got)
        self.assertIn(got,{r["ref"] for r in fit})
        self.assertGreater(work,0)
        self.assertEqual(original,model.checkpoint())

    def test_learned_realizers_do_not_need_dev_truth(self):
        fit=self.roles["L7_TRAIN"][:40]
        row=self.roles["L7_DEV"][0]
        for arm in ARMS:
            model=PublicLanguageRealizer(arm,fit)
            cp=model.checkpoint()
            output,ops=model.generate(row["mr"])
            self.assertTrue(output)
            self.assertGreater(ops,0)
            self.assertNotIn("{{",output)
            self.assertEqual(model.checkpoint(),cp)

    def test_canonical_facts_copy_every_supplied_slot(self):
        meaning={"name":"The Eagle","food":"French","near":"Burger King"}
        model=PublicLanguageRealizer("CANONICAL_FACTS",self.roles["L7_TRAIN"][:4])
        text,_=model.generate(meaning)
        for value in meaning.values():
            self.assertTrue(contains_value(text,value))
        self.assertEqual(len(PLACEHOLDER.findall(text)),0)

    def test_literal_coverage_is_not_conflated_with_natural_fluency(self):
        self.assertTrue(contains_value("The Eagle makes pasta","The Eagle"))
        self.assertFalse(contains_value("The Eagle makes pasta","The Eaglet"))
        self.assertAlmostEqual(token_f1("a b c","a b c"),1.0)
        self.assertLess(token_f1("a b c","d e f"),0.01)

    def test_held_public_scoring_does_not_mutate_trained_patterns(self):
        fit=self.roles["L7_TRAIN"][:50]
        model=PublicLanguageRealizer("DELEX_TEMPLATE",fit)
        original=model.checkpoint()
        inventory={k:{r["mr"][k] for r in fit if k in r["mr"]}
                   for k in ("name","near")}
        results=evaluate(model,self.roles["L7_DEV"][:10],inventory)
        self.assertEqual(results["records"],10)
        self.assertEqual(len(results["generated_output_sha256"]),64)
        self.assertGreaterEqual(results["exact_literal_slot_hits"],0)
        self.assertEqual(model.checkpoint(),original)


if __name__=="__main__":
    unittest.main()
