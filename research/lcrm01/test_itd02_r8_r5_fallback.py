"""Exercise native R5 fallback custody without any MiniGrid episodes."""
import unittest
from itd02_r8_r5_fallback import NativeR5Fallback

class Bridge:
    def __init__(self):self.calls=[]
    def request(self,op,**kwargs):
        self.calls.append((op,kwargs))
        if op=="choose":return {"action":2}
        if op=="feedback":return {"steps":1}
        return {"ok":True}

class FallbackTest(unittest.TestCase):
    def test_selected_feedback_only(self):
        b=Bridge();f=NativeR5Fallback(b)
        f.begin_episode()
        wire={"X":1}
        self.assertEqual(f.choose(None,wire),2)
        with self.assertRaises(ValueError):f.choose(None,wire)
        with self.assertRaises(ValueError):f.feedback(wire,1,wire)
        self.assertEqual(f.feedback(wire,2,wire),{"steps":1})
        self.assertEqual([x[0] for x in b.calls],["episode_start","choose","feedback"])
    def test_override_never_claimed(self):
        f=NativeR5Fallback(Bridge())
        with self.assertRaisesRegex(RuntimeError,"NOT_QUALIFIED"):
            f.assert_override_supported()

if __name__=="__main__":unittest.main()
