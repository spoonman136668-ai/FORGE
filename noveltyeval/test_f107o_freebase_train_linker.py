"""F107-O synthetic source/lexicon/semantic-boundary adverse tests."""
import copy
import hashlib
import json
import unittest
from pathlib import Path
from unittest import mock

import f107o_freebase_train_linker as f


def make_row(id_value: str, q: str, mention: str, mid: str, answer: str="PRIVATE"):
    return {
        "Question-ID": id_value,
        "RawQuestion": q,
        "ProcessedQuestion": "DO NOT CONSULT",
        "Parses": [{
            "PotentialTopicEntityMention": mention,
            "TopicEntityName": mention,
            "TopicEntityMid": mid,
            "InferentialChain": ["/film/film/directed_by", "/people/person/parents"],
            "Answers": [{"AnswersName": answer, "AnswersMid": "/m/private"}],
        }],
    }


class StrictTrainOnlySourceTests(unittest.TestCase):
    def test_original_train_annotation_answer_mutation_no_runtime_effect(self):
        rows = [
            make_row("q1", "Who directed The Movie Alpha?", "The Movie Alpha", "/m/alpha"),
            make_row("q2", "Where is the film Beta?", "Beta", "/m/beta"),
        ]
        mutated=copy.deepcopy(rows)
        mutated[0]["Parses"][0]["Answers"][0]["AnswersName"]="WRONG LABEL"
        mutated[1]["Parses"][0]["Answers"][0]["AnswersMid"]="/m/forged"
        first, a=f.construct_lexicon(rows)
        second,b=f.construct_lexicon(mutated)
        self.assertEqual(first,second)
        self.assertEqual(a,b)
        for q in ("Who directed The Movie Alpha?", "Where is the film Beta?"):
            self.assertEqual(f.link(q,first),f.link(q,second))
        self.assertNotIn("PRIVATE",json.dumps(a))
        self.assertNotIn("/film/film/directed_by",json.dumps(a))

    def test_train_conflicting_mid_ambiguous_abstains(self):
        rows = [
            make_row("q1", "Who directed [Case]?", "Case", "/m/a"),
            make_row("q2", "Who directed [Case]?", "Case", "/m/b"),
            make_row("q3", "Who directed Other Film?", "Other Film", "/m/c"),
        ]
        lex,stats=f.construct_lexicon(rows)
        self.assertEqual(stats["lexicon_ambiguous_mid_mentions"],1)
        self.assertEqual(f.link("Who directed Case?",lex),"ambiguous_train_lexicon")
        self.assertEqual(f.link("Who directed Other Film?",lex),"lexical_anchor_resolved")
        self.assertEqual(f.link("Case & Other Film?",lex),"ambiguous_train_lexicon")

    def test_multiple_unique_entity_hits_denied_without_selection(self):
        rows=[make_row("a","A?", "Alpha", "/m/a"),make_row("b","B?","Beta","/m/b")]
        lex,_=f.construct_lexicon(rows)
        self.assertEqual(f.link("Alpha met Beta",lex),"multiple_candidate_anchors")
        self.assertEqual(f.link("nothing recognized",lex),"no_lexical_anchor")

    def test_unicode_nfkc_case_whitespace_exact_word_boundaries(self):
        rows=[
            make_row("a","x?","The Movie", "/m/abc"),
            make_row("b","y?","ＨＥＬＬＯ", "/m/def"),
        ]
        lex,_=f.construct_lexicon(rows)
        self.assertEqual(f.link("Who directed   THE\tMovie ?",lex),"invalid_question")
        self.assertEqual(f.link("Who directed THE   Movie ?",lex),"lexical_anchor_resolved")
        self.assertEqual(f.link("who met hello ?",lex),"lexical_anchor_resolved")
        self.assertEqual(f.link("What moviemaker?",lex),"no_lexical_anchor")

    def test_no_guess_from_longer_than_frozen_ngram(self):
        name=" ".join("token%d"%i for i in range(11))
        rows=[make_row("q","who?",name,"/m/x")]
        lex,stats=f.construct_lexicon(rows)
        self.assertEqual(stats["lexicon_distinct_normalized_mentions"],0)
        self.assertEqual(f.link(name,lex),"no_lexical_anchor")
        self.assertEqual(f.link("A "*129,lex),"oversize_question_tokens")

    def test_parse_annotation_malformed_skips_but_not_gold_based(self):
        rows=[
            make_row("a","Who?","X", "/m/a"),
            {"Question-ID":"b","RawQuestion":"Unknown person?","Parses":[]},
            make_row("c","What?","Y","BAD MID"),
        ]
        lex,stats=f.construct_lexicon(rows)
        self.assertEqual(stats["original_train_rows"],3)
        self.assertEqual(stats["parse_structures"]["rows_without_parse_list"],1)
        self.assertEqual(stats["parse_structures"]["parse_entries_without_valid_mid"],1)
        self.assertEqual(len(lex),1)

    def test_duplicate_ids_and_control_question_whole_source_denied(self):
        source=[make_row("dup","A?","A","/m/a"),make_row("dup","B?","B","/m/b")]
        with self.assertRaises(f.Denied):f.construct_lexicon(source)
        for q in ("","Question\nAnswer","Question\tAnswer",chr(0)+"x","Q"*2049):
            with self.assertRaises(f.Denied):
                f.construct_lexicon([make_row("a",q,"A","/m/a")])

    def test_source_reader_rejects_dev_eval_file_bytes_without_git(self):
        for name in (f.EVAL_FILE,f.DEV_FILE,"FreebaseQA-partial.json"):
            with self.assertRaises(f.Denied):
                f.git_meta(Path("."),["show","HEAD:"+name])
        with self.assertRaises(f.Denied):
            f.git_meta(Path("."),["rev-parse","HEAD:unapproved.json"])

    def test_exact_git_object_authentication_hash(self):
        raw=b'{"Questions":[]}\n'
        original=hashlib.sha1(b"blob "+str(len(raw)).encode()+bytes([0])+raw).hexdigest()
        self.assertEqual(f.blob_id(raw),original)
        self.assertNotEqual(f.blob_id(raw.replace(b"\n",b"\r\n")),original)

    def test_permutation_invariance_of_counts(self):
        rows=[
            make_row("a","Who directed film X?","film X","/m/x"),
            make_row("b","What about film Y?","film Y","/m/y"),
            make_row("c","Where is film Z?","film Z","/m/z"),
        ]
        a,s1=f.construct_lexicon(rows)
        b,s2=f.construct_lexicon(list(reversed(rows)))
        self.assertEqual(a,b)
        self.assertEqual(s1,s2)
        self.assertEqual([f.link(x["RawQuestion"],a) for x in rows],
                         [f.link(x["RawQuestion"],b) for x in rows])


if __name__=="__main__":
    unittest.main()
