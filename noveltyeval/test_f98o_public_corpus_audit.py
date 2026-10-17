"""F98-O synthetic adversarial *source-contract* tests. No real external
Git authentication or accepted scientific testing occurs in unit tests."""
import copy
import json
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import f98o_public_corpus_audit as audit

def fixture():
    files = {
        "kg": b"Movie X|directed_by|Jane Doe\nfilm|written_by|writer\n",
        "qa2": ("Who directed [Movie X]?\tJane Doe\n" * 14872).encode(),
        "qa3": ("Which writer is linked to [film]?\twriter\n" * 14274).encode(),
    }
    blobs = {k:sha for k,_,sha,_ in audit.FILES}
    return files,blobs

class F98OSourceContract(unittest.TestCase):
    def test_bounded_complete_mirror_metadata_not_science(self):
        files,blobs=fixture()
        result=audit.inspect(pathlib.Path("."),actual_git_head=audit.UPSTREAM_HEAD,
                             raw_files=files,git_blobs=blobs)
        self.assertEqual(result["schema"],audit.SCHEMA)
        self.assertEqual(result["two_hop_denominator"],14872)
        self.assertEqual(result["three_hop_denominator"],14274)
        self.assertEqual(result["source_triple_denominator"],2)
        self.assertFalse(result["real_git_object_readback_performed"])
        self.assertFalse(result["independent_science_custody_verified"])
        for field in ("f95_test_accuracy_computed","independent_blinded_holdout_verified",
                      "authentic_scientific_original_firstuse",
                      "causal_scientific_superiority_established",
                      "dream_pareto_promotion_authorized",
                      "thetaevolve_accepted_training_allowed",
                      "science_dispatch_authorized","accepted_ref_mutation"):
            self.assertFalse(result[field],field)
        self.assertEqual(result["model_calls"],0)

    def test_source_missing_incomplete_and_wrong_git_object_quarantined(self):
        mods={
            "bad head":lambda f,b:None,
            "truncated qa":lambda f,b:f.__setitem__("qa2",f["qa2"][:-32]),
            "missing archive":lambda f,b:f.pop("qa3"),
            "wrong blob":lambda f,b:b.__setitem__("kb","f"*40),
            "empty knowledge base":lambda f,b:f.__setitem__("kg",b""),
            "malformed triple":lambda f,b:f.__setitem__("kg",b"a|b\n"),
            "missing topic brackets":lambda f,b:f.__setitem__("qa3",b"Where is it?\tname\n"*14274),
            "malformed answer":lambda f,b:f.__setitem__("qa3",b"[a] relates?\tx|\n"*14274),
            "wrong qa population":lambda f,b:f.__setitem__("qa2",b"[a] relates?\tx\n"*14871),
            "extra bad line":lambda f,b:f.__setitem__("kg",b"a|r|b\n\n"),
        }
        for name,mutate in mods.items():
            with self.subTest(name=name):
                files,blobs=fixture()
                mutate(files,blobs)
                head=audit.UPSTREAM_HEAD if name!="bad head" else "0"*40
                with self.assertRaises(audit.Blocked):
                    audit.inspect(pathlib.Path("."),actual_git_head=head,
                                  raw_files=files,git_blobs=blobs)
    def test_f95_schema_barrier_detected_without_answer_shortcuts(self):
        record=audit.kb_counts(
            b"valid|owns|thing\nAnother Entity|directed_by|A Person\n")
        self.assertEqual(record["triples"],2)
        self.assertEqual(record["f95_identifier_compatible_triples"],1)
        self.assertEqual(record["f95_identifier_incompatible_triples"],1)
        self.assertFalse(record["all_entities_can_be_loaded_without_relabeling"])
        self.assertTrue(record["entire_kb_fits_f95_128_edge_cap"])
        huge=b"a|role|b\n"*129
        self.assertFalse(audit.kb_counts(huge)["entire_kb_fits_f95_128_edge_cap"])

if __name__=="__main__":
    unittest.main()
