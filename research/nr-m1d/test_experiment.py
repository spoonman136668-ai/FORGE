"""Post-result engineering regression checks; not prospectively pre-registered science."""
import random
import unittest
from experiment import make_episode, retain, action, train, evaluate, SPLITS

class RetentionDiagnosticTests(unittest.TestCase):
    def test_generator_target_is_correct(self):
        for split in SPLITS:
            rng=random.Random(110)
            for _ in range(50):
                seq, q, target=make_episode(rng,split)
                cues=(2,3) if split=='unseen_relevant_feature_ids_2_3' else (0,1)
                cue_bits={f:b for f,b in seq if f in cues}
                self.assertEqual(target, cue_bits[q] if isinstance(q,int) else cue_bits[q[1]] ^ cue_bits[q[2]])

    def test_memory_never_exceeds_two_slots(self):
        for split in SPLITS:
            seq,q,y=make_episode(random.Random(18),split)
            for method,weights in [('fifo',None),('reservoir',None),('feature',[0.]*10),('position',[0.]*2)]:
                mem,_=retain(seq,method,random.Random(18),weights)
                self.assertEqual(len(mem),2)

    def test_training_does_not_see_future_query(self):
        seq,_,_=make_episode(random.Random(17),'in_distribution')
        # The retention function accepts (seq, method, rng, weights) but no query or target.
        mem,grad=retain(seq,'feature',random.Random(17),[0.]*10,True)
        self.assertEqual(len(grad),10)
        self.assertEqual(len(mem),2)

    def test_deterministic_training_and_evaluation(self):
        for method in ('feature','position'):
            w1, r1, _=train(17,method)
            w2, r2, _=train(17,method)
            self.assertEqual(w1,w2)
            self.assertEqual(r1,r2)
            self.assertEqual(evaluate(17,'in_distribution',method,w1)['accuracy'],
                             evaluate(17,'in_distribution',method,w2)['accuracy'])

    def test_reproduce_retained_negative_seed(self):
        weights=train(17,'feature')[0]
        actual=evaluate(17,'unseen_relevant_feature_ids_2_3','feature',weights)
        # Observed after the original experiment; post-result regression only.
        self.assertEqual(actual['accuracy'],0.4775)

if __name__=='__main__':unittest.main()
