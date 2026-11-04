"""G103 original-model diagnostic frozen contract: model-free."""
import unittest
from research.cpu_g97.g103_original_blocks import GROUPS, MODES, decision, evaluate


class G103OriginalDevelopmentTests(unittest.TestCase):
    @staticmethod
    def record(modeled, raw=3000, zlib=2600):
        return {"all_exact":True,"raw_bytes":raw,
                "independent_zlib_bytes":zlib,
                "shared_total_modeled_bytes":modeled}

    def test_positive_duplicate_group_cannot_substitute_related_win(self):
        groups = {
            "identical":{"identical_input":True,"arms":{k:self.record(500) for k in MODES}},
            "related":{"identical_input":False,"arms":{
                "fixed":self.record(2800),"adaptive":self.record(2400)}},
            "unrelated":{"identical_input":False,"arms":{k:self.record(3100) for k in MODES}}}
        self.assertEqual(decision(groups),"STRUCTURAL_NO_GO_DIAGNOSTIC")
        groups["related"]["arms"]["adaptive"]["shared_total_modeled_bytes"]=2200
        self.assertEqual(decision(groups),"STRUCTURAL_FEASIBLE_DIAGNOSTIC")
        groups["related"]["identical_input"]=True
        with self.assertRaisesRegex(RuntimeError,"CONTROL_IDENTITIES"):
            decision(groups)

    def test_incomplete_and_nonexact_fail_closed(self):
        with self.assertRaisesRegex(RuntimeError,"INCOMPLETE"):
            decision({})
        groups={n:{"identical_input":n=="identical",
                   "arms":{k:self.record(1) for k in MODES}} for n in GROUPS}
        groups["related"]["arms"]["fixed"]["all_exact"]=False
        with self.assertRaisesRegex(RuntimeError,"EXACTNESS"):
            decision(groups)

    def test_real_storage_exact_and_control_accounting(self):
        a=b"abcde"*800
        b=bytearray(a)
        b[400]^=1
        states=[a,bytes(b),a]
        measured=evaluate(states)
        for mode in MODES:
            r=measured[mode]
            self.assertTrue(r["all_exact"])
            self.assertEqual(r["raw_bytes"],sum(map(len,states)))
            self.assertEqual(r["shared_total_modeled_bytes"],
                             r["physical_payload_bytes"]+r["metadata_modeled_bytes"])
            self.assertEqual(len(r["decode_wall_ns"]),len(states))

    def test_invalid_states_fail_before_inference(self):
        with self.assertRaisesRegex(RuntimeError,"STATE_CONTRACT"):
            evaluate([b"ab"])
        with self.assertRaisesRegex(RuntimeError,"STATE_CONTRACT"):
            evaluate([b"ab",b""])


if __name__ == "__main__":
    unittest.main()
