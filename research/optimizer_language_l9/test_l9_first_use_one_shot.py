"""L9 one-shot audit runner admission tests; invented inputs ONLY, no source checkout."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import json
import unittest
import l9_first_use_one_shot as one
import l9_first_use_source_pipeline as pipe
import l9_first_use_scoring_core as score
import l9_audit_pre_admission as admission
import l9_model_suite as model
import l9_split_builder as split

REF_SENTINEL="SECRET_NEVER_PERSIST_REFERENCE_610494"
def invented_category():
    for k in range(300):
        value="invented-heldout-custody-"+str(k)
        if split.category_partition(value)=="L9_AUDIT_CATEGORY":return value
    raise ValueError("missing invented category")
def made_graph():
    triples=(model.Triple("Synthetic_Alice","livesIn","Synthetic_Boston"),)
    digest=split.graph_identity(tuple((t.subject,t.predicate,t.object) for t in triples))
    return pipe.GraphOnly(invented_category(),digest,triples,"e"*40,0)

class OneShotTests(unittest.TestCase):
    def test_default_fails_before_any_source_access_or_output(self):
        with TemporaryDirectory() as tmp:
            p=Path(tmp);out=p/"result.json"
            with patch.object(one.dev,"load_train_select",side_effect=AssertionError("source touched")):
                with self.assertRaisesRegex(ValueError,"unqualified one-time execution"):
                    one.run(p,p,p/"missing",p/"missing",p/"missing",p/"missing",out)
            self.assertFalse(out.exists())

    def test_authentication_guards_fail_on_missing_provenance(self):
        with TemporaryDirectory() as tmp:
            p=Path(tmp)
            with patch.object(one.dev,"load_train_select",side_effect=AssertionError("source touched")):
                with self.assertRaises(FileNotFoundError):
                    one.run(p,p,p/"missing_contract",p/"missing_select",
                            p/"missing_pre",p/"missing_candidate",p/"out.json",True)
            self.assertFalse((p/"out.json").exists())

    def test_existing_receipt_never_overwritten(self):
        with TemporaryDirectory() as tmp:
            p=Path(tmp);out=p/"out.json"
            out.write_text("PRESERVE")
            with self.assertRaisesRegex(ValueError,"already exists"):
                one.run(p,p,p/"missing",p/"missing",p/"missing",p/"missing",out,True)
            self.assertEqual(out.read_text(),"PRESERVE")

    def test_original_reference_reader_rechecks_frozen_graph(self):
        row=made_graph()
        xml=(f'<benchmark><entries><entry category="{row.category}">'
             f'<modifiedtripleset><mtriple>Synthetic_Alice | livesIn | Synthetic_Boston</mtriple>'
             f'</modifiedtripleset><lex>{REF_SENTINEL}</lex></entry></entries></benchmark>').encode()
        with patch.object(one.dev,"git_bytes",return_value=xml) as fetch:
            r=one.original_refs_reader(Path("INVENTED"))(row)
            self.assertEqual(r,(REF_SENTINEL,))
            self.assertEqual(fetch.call_count,1)
        with patch.object(one.dev,"git_bytes",return_value=xml):
            altered=pipe.GraphOnly(row.category,"0"*64,row.triples,row.blob_oid,row.entry_index)
            with self.assertRaisesRegex(ValueError,"reference graph identity"):
                one.original_refs_reader(Path("INVENTED"))(altered)

    def test_missing_or_empty_refs_rejected(self):
        row=made_graph()
        for lex in ("",None):
            nodes="" if lex is None else "<lex></lex>"
            xml=(f'<benchmark><entry category="{row.category}">'
                  '<modifiedtripleset><mtriple>Synthetic_Alice | livesIn | Synthetic_Boston</mtriple></modifiedtripleset>'
                  f'{nodes}</entry></benchmark>').encode()
            with self.subTest(lex=lex),patch.object(one.dev,"git_bytes",return_value=xml):
                with self.assertRaisesRegex(ValueError,"missing heldout human reference"):
                    one.original_refs_reader(Path("INVENTED"))(row)

    def test_frozen_seven_arm_bundle_after_graph_only_prediction_and_reference(self):
        names=[]
        for i in range(100):
            name="random-invented-"+str(i)
            if split.category_partition(name)=="L9_AUDIT_CATEGORY":names.append(name)
            if len(names)==3:break
        self.assertEqual(len(names),3)
        graphs=[]
        for i,cat in enumerate(names):
            triples=(model.Triple("Synthetic_Person"+str(i),"livesIn","Synthetic_City"+str(i)),)
            h=split.graph_identity(tuple((t.subject,t.predicate,t.object) for t in triples))
            graphs.append(pipe.GraphOnly(cat,h,triples,"f"*40,i))
        seen=[]
        def make(arm):
            def render(triples):
                seen.append(("PREDICTION",arm))
                return triples[0].subject+" is in "+triples[0].object+"."
            return render
        render={arm:make(arm) for arm in score.ARMS}
        predictions=pipe.prediction_only_pass(graphs,render,{"0"*64},3,3)
        self.assertEqual(len(seen),21)
        def reference(row):
            self.assertEqual(sum(x[0]=="PREDICTION" for x in seen),21)
            seen.append(("REFERENCE",row.graph_sha256))
            return (REF_SENTINEL,"independent invented text")
        cases=pipe.attach_refs_after_prediction(graphs,predictions,reference,{"0"*64},3,3)
        reports=[pipe.score_precomputed_arm(arm,cases,predictions,{"livesin":["is in"]},
                 {"0"*64},3,3) for arm in score.ARMS]
        result=score.combine_reports(reports,3,3)
        text=json.dumps(result)
        self.assertNotIn(REF_SENTINEL,text)
        self.assertNotIn("Synthetic_Person",text)
        self.assertEqual(len([x for x in seen if x[0]=="REFERENCE"]),3)
        self.assertEqual(result["arm_count"],7)
        self.assertFalse(result["scientific_go"])

    def test_pinned_runtime_selection_and_no_promotion(self):
        self.assertEqual(one.QUALIFIED_TORCH,"2.5.1")
        self.assertEqual(one.PRE_ADMISSION_SHA,
          "910a5bc252b43818a8af7d4783dd4f25208c590e9b48f019bafd85faead7428f")
        self.assertEqual(one.SEAL_SHA,admission.SEAL_RAW_SHA256)
        self.assertEqual(one.RUN_SCHEMA,
          "forge.optimizer.language.l9.unfamiliar-category-one-shot-numeric-v1")
        self.assertEqual(set(pipe.EXPECTED_NEURAL),set(score.ARMS[3:]))

if __name__=="__main__":unittest.main()
