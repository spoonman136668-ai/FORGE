"""F3 public sampler transport tests, no sealed science."""
import unittest
from unittest.mock import Mock
from ygg_public_instrument import BASELINE,validate_schedule,install_public_schedule

class InstrumentTests(unittest.TestCase):
    def test_frozen_ten_read_shape(self):
        self.assertEqual(validate_schedule(BASELINE),BASELINE)
        for invalid in (((0,1),),((0,1),)*4+((0,0),),((0,1),)*4+((0,16),)):
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError):
                    validate_schedule(invalid)
    def test_isolated_public_transport_and_restoration(self):
        original=lambda *args:"original"
        holder=Mock()
        holder.y64.dual_public_samples=original
        holder.y64.y46.coordinate=lambda address,seed,episode,family,kind:address+episode
        simulator=Mock()
        simulator.m=holder
        try:
            with install_public_schedule(simulator,BASELINE):
                observed=holder.y64.dual_public_samples(67200,(3,1,9))
                self.assertEqual(set(observed),{0,1,3,5,7})
                self.assertEqual(sum(map(len,observed.values())),10)
                self.assertEqual(observed[5],{"2":7,"4":9})
                raise RuntimeError("simulated failure")
        except RuntimeError:
            pass
        self.assertIs(holder.y64.dual_public_samples,original)

if __name__=="__main__":
    unittest.main()
