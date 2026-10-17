"""F108-O adversarial source-native TRAIN-only flat original field tests."""
import copy
import hashlib
import unittest
from pathlib import Path

import f108o_train_native_flat_linker as f
from f107o_freebase_train_linker import link

def row(rid,question,mention,mid,answer="DO_NOT_READ"):
    return {"Question-ID":rid,"RawQuestion":question,"Parses":[{
        "Parse-Id":"parse-"+rid,
        "TopicEntityMid":mid,
        "TopicEntityName":mention,
        "PotentialTopicEntityMention":mention,
        "InferentialChain":"pred.a, pred.b",
        "Answers":[{"AnswersName":answer,"AnswersMid":"SECRET"}],
    }]}

class NativeFlatTrainTests(unittest.TestCase):
    def test_authentic_flat_string_fields_and_opaque_identifier_acceptance(self):
        rows=[row("a","who directed Film A","Film A","m.100"),
              row("b","who worked on Film B","Film B","/m/200")]
        lex,stats,qs=f.build(rows,2)
        self.assertEqual(stats["original_parse_entries"],2)
        self.assertEqual(stats["valid_opaque_mid_parse_entries"],2)
        self.assertEqual(stats["total_mentions"],2)
        self.assertEqual(stats["opaque_inferential_chain_length_bands"]["length_001_032"],2)
        self.assertEqual(link("who directed Film A",lex),"lexical_anchor_resolved")
        self.assertEqual(link("who worked on Film B",lex),"lexical_anchor_resolved")
        self.assertEqual(len(qs),2)

    def test_source_answer_mutation_does_not_change_lexicon_or_runtime(self):
        rows=[row("a","who directed Film A","Film A","m.100")]
        second=copy.deepcopy(rows)
        second[0]["Parses"][0]["Answers"][0]["AnswersName"]="INJECTED_LABEL"
        second[0]["Parses"][0]["Answers"][0]["AnswersMid"]="BAD_MID"
        l1,s1,q1=f.build(rows,1)
        l2,s2,q2=f.build(second,1)
        self.assertEqual(l1,l2)
        self.assertEqual(s1,s2)
        self.assertEqual(q1,q2)
        self.assertNotIn("DO_NOT_READ",str(s1))
        self.assertNotIn("INJECTED_LABEL",str(s2))

    def test_ambiguous_opaque_mid_and_competing_anchors_refuse_to_guess(self):
        rows=[row("a","What is Alpha","Alpha","m.1"),
              row("b","Who knows Alpha","Alpha","m.2"),
              row("c","What is Beta","Beta","m.3")]
        lex,stats,_=f.build(rows,3)
        self.assertEqual(stats["ambiguous_mentions"],1)
        self.assertEqual(link("Alpha is here",lex),"ambiguous_train_lexicon")
        self.assertEqual(link("Alpha and Beta",lex),"ambiguous_train_lexicon")
        self.assertEqual(link("Nothing recognized",lex),"no_lexical_anchor")
        lex2,_,_=f.build([row("a","Alpha","Alpha","m.1"),row("b","Beta","Beta","m.2")],2)
        self.assertEqual(link("Alpha met Beta",lex2),"multiple_candidate_anchors")

    def test_id_validation_no_format_guess_but_strict_source_bounds(self):
        for val in ("m.01","/m/xyz","g.abc","opaque123","m.01_more"):
            self.assertTrue(f.opaque_mid(val))
        for val in ("","hello world","x|answer","[unsafe]","\n","x"*129,"Ⅷ"):
            self.assertFalse(f.opaque_mid(val))

    def test_source_schema_mismatch_and_duplicate_ids_denied(self):
        src=[row("a","who","Who","m.1")]
        for field in ("InferentialChain","TopicEntityMid","TopicEntityName","PotentialTopicEntityMention"):
            changed=copy.deepcopy(src)
            changed[0]["Parses"][0][field]=[]
            with self.assertRaises(f.Denied):f.build(changed,1)
        with self.assertRaises(f.Denied):f.build(src+src,2)
        with self.assertRaises(f.Denied):f.build(src,2)
        with self.assertRaises(f.Denied):f.build([row("a","question\tAnswer","A","m.1")],1)

    def test_unqualified_source_dev_and_eval_content_never_retrievable(self):
        for op in (["show","HEAD:"+f.DEV],["show","HEAD:"+f.EVAL],
                   ["rev-parse","HEAD:UnapprovedFile.json"]):
            with self.assertRaises(f.Denied):f.git_meta(Path("."),op)

    def test_exact_git_object_crc_identity(self):
        raw=b'{"Questions":[]}\n'
        expect=hashlib.sha1(b"blob "+str(len(raw)).encode()+bytes([0])+raw).hexdigest()
        self.assertEqual(f.source_id(raw),expect)
        self.assertNotEqual(f.source_id(raw+b"x"),expect)

    def test_train_permutation_does_not_change_aggregate(self):
        src=[row("a","A film","Film Alpha","m.10"),
             row("b","B film","Film Beta","m.11"),
             row("c","C film","Film Alpha","m.10")]
        a,stats1,_=f.build(src,3)
        b,stats2,_=f.build(list(reversed(src)),3)
        self.assertEqual(a,b)
        self.assertEqual(stats1,stats2)

if __name__=="__main__":unittest.main()
