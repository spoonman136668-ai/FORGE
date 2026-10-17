"""F124-N source-before-mechanism qualification; no protected science."""
import hashlib
import json
from pathlib import Path
import unittest

import f124n_novel_structure_source as source
import f124n_development_evidence as evidence


class F124NSourceTests(unittest.TestCase):
    def test_exact_frozen_identity_and_disjoint_cohorts(self):
        self.assertEqual(source.git_blob(source.PROTOCOL.read_bytes().replace(b"\r\n",b"\n")),
                         source.PROTOCOL_BLOB)
        self.assertEqual(len(source.frozen()), 64)
        for lane, cohorts in source.COHORTS.items():
            self.assertTrue(set(cohorts["FIT"]).isdisjoint(cohorts["DEV"]))
            self.assertTrue(set(cohorts["FIT"]).isdisjoint(source.FORBIDDEN[lane]))
            self.assertTrue(set(cohorts["DEV"]).isdisjoint(source.FORBIDDEN[lane]))
            for phase in ("FIT","DEV"):
                with self.assertRaises(source.Quarantined):
                    source.build(lane, next(iter(source.FORBIDDEN[lane])),
                                 source.VECTORS[0], phase)
        with self.assertRaises(source.Quarantined):
            source.protected(lane="Wingless",seed=180100)

    def test_complete_fresh_public_pair_source(self):
        for lane in ("Wingless","Yggdrasil"):
            for phase in ("FIT","DEV"):
                seen = set()
                depths = {7:0,8:0,9:0}
                reused = 0
                partial = 0
                for vector in source.VECTORS:
                    for seed in source.COHORTS[lane][phase]:
                        positive,negative = source.build(lane,seed,vector,phase)
                        self.assertTrue(source.paired_admit(positive,negative))
                        depths[len(positive["roles"])] += 1
                        reused += len(set(positive["roles"])) < len(positive["roles"])
                        partial += any(all(not b for b in e["src_bits"]+e["dst_bits"])
                                       for e in positive["edges"])
                        digest = hashlib.sha256(
                            json.dumps(positive,sort_keys=True).encode()).hexdigest()
                        self.assertNotIn(digest, seen)
                        seen.add(digest)
                self.assertEqual(depths,{7:16,8:16,9:16})
                self.assertGreater(reused,0)
                self.assertEqual(partial,48)
                self.assertEqual(len(seen),48)

    def test_original_forward_unchanged_and_no_forged_receipt(self):
        self.assertEqual(evidence.blob(evidence.old_model),evidence.MODEL_BLOB)
        self.assertEqual(evidence.blob(evidence.old_source),evidence.SOURCE_BLOB)
        fwd=evidence.clone_single_validator(evidence.old_model.forward,"source")
        fixed=evidence.clone_single_validator(evidence.old_control.fixed_comparator,"graph")
        self.assertIs(fwd.__code__, evidence.old_model.forward.__code__)
        self.assertIs(fixed.__code__, evidence.old_control.fixed_comparator.__code__)
        self.assertIs(evidence.old_model.forward.__globals__["source"], evidence.old_source)
        with self.assertRaises(source.Quarantined):
            evidence.authenticate(Path(__file__).resolve())  # Not an authentic receipt.
        with self.assertRaises(source.Quarantined):
            source.validate_public({"label":True,"reserved_oracle":1})


if __name__=="__main__":
    unittest.main()
