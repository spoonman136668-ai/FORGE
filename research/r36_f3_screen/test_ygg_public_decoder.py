"""F3 public-only decoder qualification against fixed-budget observations."""
import unittest
from ygg_public_decoder import decode_public

def coords(t,c,a=5,b=3,d=1):
    return (b+t*d+c*a)%16

def reading(first=(8,10),extra=None):
    x={0:{"0":coords(0,0),"1":coords(0,1)},
       1:{"0":coords(1,0),"1":coords(1,1)},
       3:{"0":coords(3,0),"1":coords(3,1)},
       5:{"8":coords(5,first[1]),"11":coords(5,11)},
       7:{"0":coords(7,0),"1":coords(7,1)}}
    if extra is not None:x[7]=extra
    return x

class PublicDecoderTests(unittest.TestCase):
    def test_nonfixed_public_sensor_is_causally_consumed(self):
        obs=reading()
        self.assertIsNone(decode_public(obs,3)["first_detection_episode"])
        out=decode_public(obs,7)
        self.assertEqual(out["first_detection_episode"],5)
        self.assertEqual(out["detected_pair"],{8:10,10:8})
    def test_steady_sensor_reads_have_no_detection(self):
        obs=reading()
        obs[5]["8"]=coords(5,8)
        for t in (3,5,7):
            self.assertIsNone(decode_public(obs,t)["first_detection_episode"])
    def test_incompatible_second_public_swap_fails_closed(self):
        obs=reading(extra={"2":coords(7,4),"4":coords(7,4)})
        with self.assertRaisesRegex(ValueError,"F3_SECOND_INDEPENDENT_SWAP"):
            decode_public(obs,7)
    def test_calibration_tamper_is_rejected(self):
        obs=reading()
        obs[1]["1"]+=2
        with self.assertRaisesRegex(ValueError,"F3_PUBLIC_CALIBRATION_DRIFT"):
            decode_public(obs,7)
if __name__=="__main__":
    unittest.main()
