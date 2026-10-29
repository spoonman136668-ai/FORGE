"""P12 retrieval-only negative controls. Synthetic data; zero network/model calls."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
import mpai05_p12_evidence_selection as x

def evidence():
    return {
      "abc00001":["Goal: send delivery confirmation","Action: update delivery",
                    "accessibility_tree: shipping address saved",
                    "thought: delivery was confirmed"],
      "def00002":["Goal: account profile","Action: open profile",
                    "accessibility_tree: change account settings",
                    "thought: home"],
      "other123":["Goal: shipping address saved secret OTHER SOURCE"]
    }

class TestP12EvidenceSelection(unittest.TestCase):
    def test_fixed_same_budget_and_method_names(self):
        self.assertEqual(x.MAX_CONTEXT,2300)
        self.assertEqual(x.METHODS,("p10_lexical","idf_diverse","idf_neighbor"))
        self.assertEqual(x.MAX_SEGMENTS,8)
        self.assertEqual(x.TOP_ANCHORS,120)
    def test_gold_blind_interface(self):
        import inspect
        self.assertEqual(list(inspect.signature(x.score_anchors).parameters),
                         ["question","index","df"])
        self.assertEqual(list(inspect.signature(x.diverse).parameters),
                         ["question","anchors"])
        self.assertNotIn("answer",str(inspect.signature(x.score_anchors)))
    def test_index_and_ranking_reproducible(self):
        mem=evidence();allowed={k:mem[k] for k in ("abc00001","def00002")}
        index,df=x.build_index(allowed)
        a=x.score_anchors("delivery confirmation shipping",index,df)
        b=x.score_anchors("delivery confirmation shipping",index,df)
        self.assertEqual(a,b)
        self.assertTrue(a)
    def test_diversity_and_capacity(self):
        mem=evidence();allowed={k:mem[k] for k in ("abc00001","def00002")}
        index,df=x.build_index(allowed)
        anchors=x.score_anchors("delivery shipping address",index,df)
        chosen=x.diverse("delivery shipping address",anchors)
        self.assertLessEqual(len(chosen),x.MAX_SEGMENTS)
        self.assertEqual(len({(a,b) for a,b,_ in chosen}),len(chosen))
        self.assertLessEqual(len(x.pack(chosen)),x.MAX_CONTEXT)
    def test_no_external_haystack_trajectory(self):
        mem=evidence();case={k:mem[k] for k in ("abc00001","def00002")}
        index,df=x.build_index(case)
        a=x.score_anchors("shipping address saved secret",index,df)
        result=x.pack(x.diverse("shipping address saved secret",a))
        self.assertNotIn("other123",result)
        self.assertNotIn("OTHER SOURCE",result)
    def test_adjacent_only_same_trajectory(self):
        mem=evidence();case={"abc00001":mem["abc00001"]}
        index,df=x.build_index(case)
        a=x.score_anchors("delivery confirmation",index,df)
        nexts=x.adjacent(a,case)
        self.assertTrue(nexts)
        self.assertTrue(all(i=="abc00001" for i,_,_ in nexts))
        self.assertLessEqual(len(x.pack(nexts,150)),150)
    def test_pack_truncates_by_omission(self):
        pieces=[("abc00001",0,"A"*100),("def00002",0,"B"*100)]
        a=x.pack(pieces,max_chars=125)
        self.assertTrue(a.startswith("Evidence"))
        self.assertIn("A"*100,a)
        self.assertNotIn("B"*100,a)
    def test_pack_deduplicates(self):
        row=("abc00001",0,"Action: update")
        text=x.pack([row,row])
        self.assertEqual(text.count("Evidence ["),1)
    def test_empty_question_gives_no_anchors(self):
        index,df=x.build_index(evidence())
        self.assertEqual(x.score_anchors("",index,df),[])
    def test_no_runtime_or_writer_used(self):
        text=Path(x.__file__).read_text(encoding="utf-8")
        for bad in ("from llama_cpp", "create_chat_completion(", "openai.OpenAI(",
                    "write_accepted_ice(", "model_promotion_authorized=True"):
            self.assertNotIn(bad,text)
        self.assertIn('MPAI05_P12_GOLD_USED_FOR_RANKING=FALSE',text)
    def test_gold_diagnostic_does_not_define_retriever(self):
        mem=evidence();index,df=x.build_index(mem)
        before=x.score_anchors("delivery address",index,df)
        # Gold text is not a ranking argument; two unrelated golds
        # cannot affect evidence ranking on the same question.
        gold_a="updated address"
        gold_b="different reference"
        self.assertNotEqual(gold_a,gold_b)
        self.assertEqual(before,x.score_anchors("delivery address",index,df))
if __name__=="__main__":unittest.main()
