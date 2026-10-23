"""L1 bounded source/custody tests. No model training, DEV selection or science."""
import hashlib
import json
import math
import unittest

from public_source import (
    NAMESPACE,ROLES,COUNTS,ACTORS,VERBS,OBJECTS,MODIFIERS,
    SourceCustodyDenied,seed,semantic_holdout,semantics,realize,
    public_record,public_role,digest,canonical,
)


class L1SourceOnlyQualification(unittest.TestCase):
    def test_frozen_charter_is_additive_to_existing_research(self):
        from pathlib import Path
        charter=json.loads((Path(__file__).parent/
                            "L1_FROZEN_CHARTER.json").read_text(encoding="utf-8"))
        self.assertEqual(
            charter["status"],
            "PROSPECTIVELY_FROZEN_BEFORE_GENERATOR_IMPLEMENTATION")
        self.assertEqual(charter["governance"]["mode"],"ADDITIVE_EXPLORATORY_ONLY")
        preserved=charter["governance"]["no_displacement"]
        for name in ("NCI-04","ITD-01","BIO","Mass Research",
                     "Optimizer native learning","Q21 successor","FORGE controller/custody"):
            self.assertIn(name,preserved)
        self.assertEqual(charter["l1_status"],
                         "SOURCE_AND_PROTOCOL_ONLY_NO_CANDIDATE_TRAINED_OR_SCIENTIFIC_VALIDATION")

    def test_exact_roles_and_episode_budget(self):
        self.assertEqual(len(ROLES),4)
        self.assertEqual(sum(COUNTS.values()),368)
        for role in ROLES:
            self.assertEqual(len(public_role(role)),COUNTS[role])

    def test_protected_and_old_experiment_roles_refused(self):
        for role in ("HELD","ORIGINAL","Q21","Q21N01","O14_ZERO_SHOT_TRANSFER",
                     "O13_PUBLIC_DEV","L1_PUBLIC_DEV","FIT_TRAIN"):
            with self.assertRaises(SourceCustodyDenied):
                public_role(role)
        for role in ROLES:
            for invalid in (-1,COUNTS[role],True,1.0,"0"):
                with self.assertRaises(SourceCustodyDenied):
                    seed(role,invalid)

    def test_independently_seeded_records_are_reproducible(self):
        for role in ROLES:
            for i in (0,COUNTS[role]//2,COUNTS[role]-1):
                self.assertEqual(public_record(role,i),public_record(role,i))
                raw=f"{NAMESPACE}:{role}:{i}".encode("ascii")
                self.assertEqual(seed(role,i),int.from_bytes(
                    hashlib.sha256(raw).digest()[:8],"big"))

    def test_no_exact_fit_or_selection_tuple_appears_in_composition_dev(self):
        train={s for s,_ in public_role("L1_FIT_TRAIN")}
        select={s for s,_ in public_role("L1_FIT_SELECT")}
        dev={s for s,_ in public_role("L1_PUBLIC_DEV_COMPOSE")}
        self.assertEqual(len(train),COUNTS["L1_FIT_TRAIN"])
        self.assertEqual(len(select),COUNTS["L1_FIT_SELECT"])
        self.assertEqual(len(dev),COUNTS["L1_PUBLIC_DEV_COMPOSE"])
        self.assertFalse(train & select)
        self.assertFalse((train|select)&dev)
        self.assertTrue(all(not semantic_holdout(s) for s in train|select))
        self.assertTrue(all(semantic_holdout(s) for s in dev))

    def test_fit_corpus_has_public_lexeme_and_polality_coverage(self):
        train=public_role("L1_FIT_TRAIN")
        for field,n in enumerate((6,6,6,5,2)):
            self.assertEqual({s[field] for s,_ in train},set(range(n)))

    def test_all_realizations_are_canonical_and_semantically_recoverable(self):
        for role in ROLES[:-1]:
            for s,tok in public_role(role):
                self.assertEqual(tuple(tok),realize(s))
                self.assertEqual(tok[0],"<bos>")
                self.assertEqual(tok[-1],"<eos>")
                self.assertEqual(tok[1],"the")
                self.assertEqual(tok[3],"will")
                self.assertEqual(tok[-2],".")
                self.assertEqual(tok.count("not"),s[-1])
                self.assertEqual(len(tok),10+s[-1])
                self.assertEqual(tok[2],ACTORS[s[0]])
                self.assertEqual(tok[4+s[-1]],VERBS[s[1]])
                self.assertEqual(tok[6+s[-1]],OBJECTS[s[2]])
                self.assertEqual(tok[7+s[-1]],MODIFIERS[s[3]])

    def test_null_is_explicitly_misaligned_not_language_quality(self):
        for s,tok in public_role("L1_PUBLIC_NULL"):
            actual=realize(s)
            self.assertNotEqual(tok,actual)
            self.assertNotEqual(tok[2],actual[2])
            self.assertNotEqual(tok[4+s[-1]],actual[4+s[-1]])
            self.assertNotEqual(tok[6+s[-1]],actual[6+s[-1]])
        # Null perturbation must not remove polarity, punctuation or grammar.
        self.assertEqual(tok.count("not"),s[-1])
        self.assertEqual(tok[0],"<bos>")

    def test_source_identity_has_four_different_sha256_digests(self):
        hashes=[digest(role) for role in ROLES]
        self.assertEqual(len(set(hashes)),4)
        self.assertTrue(all(len(h)==64 for h in hashes))
        self.assertEqual(digest(ROLES[0]),digest(ROLES[0]))

    def test_realize_denies_out_of_range_or_privileged_payload(self):
        bad=((0,0,0,0,2),(6,0,0,0,0),("hidden",0,0,0,0),
             (0,0,0,0,0,"private_source"),(0,0,0,0,1.0))
        for x in bad:
            with self.assertRaises(ValueError):
                realize(x)
        with self.assertRaises(SourceCustodyDenied):
            public_record("FSA_FIRST_USE",0)


if __name__=="__main__":
    unittest.main()
