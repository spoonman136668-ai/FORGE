"""AC-19 lossless typed source-code injection and frozen control guards.

Fixtures exercise adapter validation only, not synthetic scientific trials.
"""
import unittest
import ac19_typed_original_native_bridge as a

class AC19Tests(unittest.TestCase):
    def test_exhaustive_round_trip_input_outcome_categories(self):
        result=a.ensure_exhaustive_roundtrips()
        self.assertEqual(result["unique_input_vectors"],8)
        self.assertEqual(result["unique_output_vectors"],6)

    def test_actual_none_and_reward_one_are_distinct(self):
        terminal=a.encode_after(None,True,1)
        self.assertEqual(terminal,[0,0,1,1,0,1,0,0])
        self.assertEqual(a.decode_after(terminal),(None,True,1))
        normal=a.encode_after(0,False,1)
        self.assertNotEqual(normal,terminal)
        self.assertEqual(a.decode_after(normal),(0,False,1))
        self.assertNotEqual(terminal,a.encode_after(None,True,0))

    def test_reject_forged_successor_and_source_reward(self):
        with self.assertRaisesRegex(ValueError,"TERMINAL_SUCCESSOR"):
            a.encode_after(1,True,1)
        with self.assertRaisesRegex(ValueError,"INVALID_PUBLIC_BINARY_SUCCESSOR"):
            a.encode_after(None,False,0)
        with self.assertRaisesRegex(ValueError,"INVALID_PUBLIC_BINARY_REWARD"):
            a.encode_after(None,True,10)
        with self.assertRaisesRegex(ValueError,"INVALID_PUBLIC_BINARY_REWARD"):
            a.encode_after(None,True,True)
        with self.assertRaisesRegex(ValueError,"INVALID_PUBLIC_TERMINAL"):
            a.encode_after(1,1,0)

    def test_reject_noninjective_bits(self):
        b=a.encode_after(None,True,1)
        b[0]=1
        with self.assertRaisesRegex(ValueError,"INVALID_TYPED_OUTCOME_BITS"):
            a.decode_after(b)
        b=a.encode_after(None,True,1)
        b[3]=0
        with self.assertRaisesRegex(ValueError,"TERMINAL_MASK"):
            a.decode_after(b)
        b=a.encode_before(0,0,1)
        b[0]=1  # reserved outside original site-5 neighborhood
        with self.assertRaisesRegex(ValueError,"INVALID_TYPED_BEFORE_BITS"):
            a.decode_before(b)

    def test_all_public_contexts_accessible_within_original_reward_cell_one_hop(self):
        local={}
        for stage in (0,1):
            for observation in (0,1):
                for action in (0,1):
                    b=a.encode_before(stage,observation,action)
                    # Original LocalTaskRuntime site 5 sees self and neighbors 4,6.
                    local[(stage,observation,action)]=(b[4],b[5],b[6])
        self.assertEqual(len(set(local.values())),8)
        self.assertEqual(a.ensure_exhaustive_roundtrips()[
            "native_reward_cell_one_hop_distinguishable_public_inputs"],8)

    def test_no_outcome_target_leakage_into_native_inputs(self):
        def event(y):
            return {"stage":1,"observation":1,"action":0,
                    "next_observation":None,"reward":y,
                    "terminated":True,"truncated":False,"valid_actions":[0,1]}
        before0,after0=a.source_event_to_bits(event(0))
        before1,after1=a.source_event_to_bits(event(1))
        self.assertEqual(before0,before1)
        self.assertNotEqual(after0,after1)
        self.assertEqual(after0[5],0)
        self.assertEqual(after1[5],1)

    def test_source_event_whitelist_rejects_oracle(self):
        ev={"stage":0,"observation":0,"action":1,
            "next_observation":0,"reward":0,"terminated":False,
            "truncated":False,"valid_actions":[0,1]}
        a.source_event_to_bits(ev)
        with self.assertRaisesRegex(ValueError,"NOT_SOURCE_PUBLIC"):
            a.source_event_to_bits(dict(ev,u=7))
        with self.assertRaisesRegex(ValueError,"SOURCE_STAGE0"):
            a.source_event_to_bits(dict(ev,reward=1))
        with self.assertRaisesRegex(ValueError,"SOURCE_STAGE1"):
            a.source_event_to_bits(dict(ev,stage=1))

    def test_matched_source_probability_metrics(self):
        got=a.metrics([.25,.75],[0,1])
        self.assertEqual(got["correct"],2)
        self.assertAlmostEqual(got["brier"],.0625)
        with self.assertRaises(RuntimeError):
            a.metrics([2.],[1])

    def test_exact_historical_genuine_native_module_pins(self):
        self.assertEqual(a.RUNTIME_BLOB,"68a1423e0bd7206af511212c14b6ce8534154cc2")
        self.assertEqual(a.ac18.RING_BLOB,"1db0835d5c99456bcf99a013d4836f49314a9d39")
        self.assertEqual(a.ac18.BRIDGE_BLOB,"b311ea7ea00c15d23e7bd43ff97bd10ce3d8b87c")
        self.assertEqual(a.ac18.YGG_COMMIT,"a39171a76d0d7817e3563682bb139a9d7ecf37c4")
        self.assertNotEqual(a.ac18.YGG_COMMIT,a.ac18.CURRENT_ACTIVE_YGG)

if __name__=="__main__":
    unittest.main()
