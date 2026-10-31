"""ACC-102 focused source-free contract tests; not scientific acceptance."""
import unittest
from interacting_cells import InteractingCells, evaluate
from switching import switching_trace

class InteractingContracts(unittest.TestCase):
    def test_isolation_delayed_message(self):
        m=InteractingCells()
        m.observe([((0,0,1),1)])
        self.assertEqual(m.incoming[0],((0,0),(0,0)))  # no current-label routing
        m.advance_messages()
        self.assertNotEqual(m.incoming[0],((0,0),(0,0)))
        self.assertEqual(m.sent_payload_bytes,32)
        self.assertEqual(m.delivered_payload_bytes,32)

    def test_zero_communication_ablation(self):
        m=InteractingCells("disabled")
        m.observe([((0,0,1),1)])
        m.advance_messages()
        self.assertEqual(m.incoming,[((0,0),(0,0))]*8)
        self.assertEqual(m.sent_payload_bytes,0)

    def test_two_byte_payload_and_counts(self):
        m=InteractingCells("connected")
        m.observe([((0,0,1),1)])
        m.advance_messages()
        self.assertEqual(m.incoming[0][0][0],1)
        self.assertTrue(all(len(message)==2 for edges in m.incoming for message in edges))
        self.assertEqual(m.sent_payload_bytes,8*2*2)
        self.assertEqual(m.delivered_payload_bytes,8*2*2)
        m.advance_messages()
        self.assertEqual(m.sent_payload_bytes,64)
        self.assertEqual(InteractingCells.restore(m.snapshot()).snapshot(),m.snapshot())

    def test_message_effect_and_complete_payload_accounting(self):
        a=InteractingCells("connected")
        b=InteractingCells("disabled")
        # Neighbor 1's positive feedback must reach cell 0 only on next tick.
        for learner in (a,b):
            learner.observe([((0,0,1),1)] * 5)
        self.assertEqual(a.predict((0,0,0)),b.predict((0,0,0)))
        a.advance_messages()
        b.advance_messages()
        self.assertEqual(a.sent_payload_bytes,32)
        self.assertEqual(a.delivered_payload_bytes,32)
        self.assertEqual(b.sent_payload_bytes,0)
        self.assertEqual(b.delivered_payload_bytes,0)
        # The neighboring cell contributes a nonzero quantized error signal.
        self.assertNotEqual(a.incoming[0][0][1],0)
        self.assertEqual(b.incoming[0],((0,0),(0,0)))

    def test_exact_full_episode_communication_cost(self):
        trace=switching_trace("DEV",54,701)
        for mode in ("connected","shuffled"):
            report=evaluate(trace,mode)
            self.assertEqual(report["payload_bytes_sent"],320*32)
            self.assertEqual(report["payload_bytes_delivered"],320*32)
        report=evaluate(trace,"disabled")
        self.assertEqual(report["payload_bytes_sent"],0)
        self.assertEqual(report["payload_bytes_delivered"],0)

    def test_shuffled_topology_not_identical(self):
        a=InteractingCells("connected")
        b=InteractingCells("shuffled")
        self.assertNotEqual(a.edges,b.edges)

    def test_restored_state_byte_identical(self):
        m=InteractingCells("connected")
        m.observe([((1,0,1),1),((0,1,0),0)])
        m.advance_messages()
        self.assertEqual(InteractingCells.restore(m.snapshot()).snapshot(),m.snapshot())
        for invalid in ('{}','{"schema":"wrong"}'):
            with self.assertRaises(ValueError):
                InteractingCells.restore(invalid)

    def test_dev_and_sealed_cohort(self):
        trace=switching_trace("DEV",54,701)
        for mode in ("connected","disabled","shuffled"):
            r=evaluate(trace,mode)
            self.assertEqual(r["phase_queries"],[2432,1216,2432])
            self.assertTrue(r["cold_restore_exact"])
            self.assertEqual(r["scientific_acceptance"],"NOT_GRANTED")
            self.assertEqual(r,evaluate(trace,mode))
        trace["reserved_test_used"]=True
        with self.assertRaises(ValueError):
            evaluate(trace)

    def test_invalid_learning_input(self):
        m=InteractingCells()
        for bad in ((1,1),(2,0,1)):
            with self.assertRaises(ValueError):
                m.predict(bad)
        with self.assertRaises(ValueError):
            m.observe([((0,0,0),2)])

if __name__=="__main__":
    unittest.main()
