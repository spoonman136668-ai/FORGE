"""AC-21 narrow tests: no source calls, no synthetic labels passed to candidate."""
import itertools
import unittest

import ac21_sequential_local_native as a


def sample_episode(s1=1, x1=0, s2=1, x2=1, reward=1):
    e0 = {"stage":0,"observation":s1,"action":x1,
          "next_observation":s2,"reward":0,"terminated":False,
          "truncated":False,"valid_actions":[0,1]}
    e1 = {"stage":1,"observation":s2,"action":x2,
          "next_observation":None,"reward":reward,"terminated":True,
          "truncated":False,"valid_actions":[0,1]}
    return {"seed":760000,"events":[e0,e1],
            "ctf_do_permission_denied":True}


class AC21SequentialNativeTests(unittest.TestCase):
    def test_stage_zero_does_not_see_stage_one_public_future(self):
        x=a.SequentialLocalLatch()
        self.assertEqual(x.advance(0,1,0),(0,0,0,1,0,0,0,0))
        with self.assertRaisesRegex(ValueError,"INCOMPLETE"):
            x.terminal_bits()
        self.assertEqual(x.advance(1,0,1),(0,0,0,1,0,0,1,0))
        self.assertEqual(x.terminal_bits(),[0,0,0,1,0,0,1,0])
        with self.assertRaisesRegex(ValueError,"STAGE_ORDER"):
            x.advance(1,1,1)

    def test_exact_four_public_bits_sequentially_encode_sixteen_histories(self):
        seen=set()
        for h in itertools.product((0,1),repeat=4):
            e=sample_episode(h[0],h[1],h[2],h[3],0)
            bits, label, writes=a.public_episode_bits(e)
            self.assertEqual(bits[3:7],list(h))
            self.assertEqual(writes,4)
            self.assertEqual(label,0)
            seen.add(tuple(bits))
        self.assertEqual(len(seen),16)

    def test_ablate_one_retained_or_current_site_only(self):
        e=sample_episode(1,1,1,1,1)
        original,_,_=a.public_episode_bits(e)
        self.assertEqual(original[3:7],[1,1,1,1])
        for site in a.HISTORY_SITES:
            masked,_,_=a.public_episode_bits(e,omit=site)
            self.assertEqual(masked[site],0)
            self.assertEqual(sum(masked[3:7]),3)
        with self.assertRaisesRegex(ValueError,"INVALID_ABLATION_SITE"):
            a.public_episode_bits(e,omit=True)

    def test_hidden_oracle_data_and_corrupt_episodes_rejected(self):
        e=sample_episode()
        e["u"]=.5
        with self.assertRaisesRegex(ValueError,"UNKNOWN_ORACLE"):
            a.public_episode_bits(e)
        e=sample_episode()
        e["events"][1]["hidden_latent"]=.5
        with self.assertRaisesRegex(ValueError,"ORACLE_FIELD"):
            a.public_episode_bits(e)
        e=sample_episode()
        e["events"][0]["next_observation"]=0
        with self.assertRaisesRegex(ValueError,"STAGE_CHAIN"):
            a.public_episode_bits(e)
        e=sample_episode()
        e["events"][0]["stage"]=1
        with self.assertRaisesRegex(ValueError,"STAGE_ORDER"):
            a.public_episode_bits(e)
        e=sample_episode()
        e["events"][1]["next_observation"]=1
        with self.assertRaisesRegex(ValueError,"TERMINAL_PUBLIC"):
            a.public_episode_bits(e)

    def test_local_reward_target_is_public_not_hidden_source_callback(self):
        self.assertEqual(a.reward_targets(0),[0]*8)
        self.assertEqual(a.reward_targets(1),[0,0,0,0,1,1,0,0])
        with self.assertRaisesRegex(ValueError,"PUBLIC_BIT"):
            a.reward_targets(True)
        with self.assertRaisesRegex(ValueError,"PUBLIC_BIT"):
            a.reward_targets(-1)

    def test_scoring_and_negative_scientific_scope(self):
        self.assertEqual(a.score([0,1],[0,1]),{"n":2,"correct":2,"brier":0})
        with self.assertRaisesRegex(ValueError,"NONPROBABILISTIC"):
            a.score([float("nan")],[1])
        with self.assertRaisesRegex(ValueError,"EMPTY_OR_MISALIGNED"):
            a.score([],[1])
        self.assertEqual(a.SOURCE_RECEIPT_RUN,40797373953)
        self.assertEqual(a.FIT_SEEDS,tuple(range(760000,760008)))
        self.assertEqual(a.DEV_SEEDS,tuple(range(760200,760204)))


if __name__=="__main__":
    unittest.main()
