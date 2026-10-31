"""ACC-102 focused source-free contract tests; not scientific acceptance."""
import unittest
from interacting_cells import InteractingCells, evaluate
from switching import switching_trace

class InteractingContracts(unittest.TestCase):
    def test_isolation_delayed_message(self):
        m=InteractingCells()
        m.observe([((0,0,1),1)])
        self.assertEqual(m.incoming[0],(0,0))  # no current-label routing
        m.advance_messages()
        self.assertNotEqual(m.incoming[0],(0,0))
        self.assertEqual(m.sent_payload_bytes,16)
        self.assertEqual(m.delivered_payload_bytes,16)

    def test_zero_communication_ablation(self):
        m=InteractingCells("disabled")
        m.observe([((0,0,1),1)])
        m.advance_messages()
        self.assertEqual(m.incoming,[(0,0)]*8)
        self.assertEqual(m.sent_payload_bytes,0)

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
