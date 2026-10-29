"""MG28 synthetic falsification controls; no original Farama env invoked."""
import unittest
from fractions import Fraction
from mg28_strong_context_action_controls import predictors,observe,new_counter,summary,WINDOW
from mg25_original_policy_activation_audit import digest

def frame(direction=0,front=(1,0,0),mission="pick up the red box"):
    image=[[[1,0,0] for _ in range(7)] for _ in range(7)]
    image[3][5]=list(front)
    return {"image":image,"direction":direction,"mission":mission}

def selected(before,after,action):
    return {"before":before,"after":after,"action":action,
            "before_sha256":digest(before),"after_sha256":digest(after),
            "reward":0.0,"terminated":False,"truncated":False}

class MG28StrongNegativeControls(unittest.TestCase):
    def test_prequential_context_only_action_only_and_full_support(self):
        b=frame();n=frame(1)
        a=selected(b,n,2)
        counter=new_counter();history=[]
        observe(counter,history,a)
        self.assertEqual(counter["steps"],1)
        self.assertEqual(counter["supported"],0)
        self.assertEqual(len(history),1)
        # Exact context+same action has support on second genuine selected event.
        observe(counter,history,a)
        self.assertEqual(counter["supported"],1)
        self.assertEqual(counter["context_supported"],1)
        self.assertEqual(counter["action_supported"],1)
        self.assertEqual(summary(counter)["original_supported_brier"]["full"],"0.1111111111")
        # New previously unseen action in the SAME context is supported by
        # context-only but not by full selected action predictor.
        observe(counter,history,selected(b,b,3))
        self.assertEqual(counter["supported"],1)
        from mg26_source_consequence_signal_audit import context
        predictions=predictors(history,context(b),3)
        self.assertEqual(predictions["full"][1],1)
        self.assertEqual(predictions["context_only"][1],3)
        self.assertEqual(predictions["action_only"][1],1)

    def test_strong_action_only_can_predict_without_context(self):
        from mg26_source_consequence_signal_audit import context
        a=frame();b=frame(2,mission="pick up the blue box")
        history=[(context(a),3,0)]
        pred=predictors(history,context(b),3)
        self.assertEqual(pred["full"],(Fraction(1,2),0))
        self.assertEqual(pred["context_only"],(Fraction(1,2),0))
        self.assertEqual(pred["action_only"],(Fraction(1,3),1))
        self.assertEqual(pred["global_only"],(Fraction(1,3),1))

    def test_future_not_used_and_window_bounded(self):
        b=frame();next_frame=frame(1)
        history=[];m=new_counter()
        first=selected(b,next_frame,2)
        for _ in range(WINDOW+10):
            observe(m,history,first)
            self.assertLessEqual(len(history),WINDOW)
        self.assertEqual(m["steps"],WINDOW+10)
        self.assertEqual(m["supported"],WINDOW+9)
        # Following event outcome must not change past scored sums.
        old=m["squared"]["full"]
        observe(m,history,selected(b,b,2))
        self.assertEqual(m["supported"],WINDOW+10)
        self.assertGreater(m["squared"]["full"],old)

    def test_corrupt_original_source_sha_is_refused(self):
        b=frame();e=selected(b,b,2)
        e["after_sha256"]="0"*64
        with self.assertRaises(ValueError):
            observe(new_counter(),[],e)

if __name__=="__main__":unittest.main()
