"""AC28 historical original-source incompatibility: focused source-free negatives."""
import json
import unittest
import ac28_source_mission_blocker as a

SOURCE='''class UnlockEnv:
    @staticmethod
    def _gen_mission():
        return "open the door"
'''
YGG='''MISSION = "use the key to open the door and then get to the goal"
def public_observation(obs):
    if obs["mission"] != MISSION:
        raise ValueError("R10_PUBLIC_MISSION")
'''

class AC28MissionContractTests(unittest.TestCase):
    def test_two_genuine_public_missions_are_not_equal(self):
        s,y=a.original_missions(SOURCE,YGG)
        self.assertEqual(s,"open the door")
        self.assertNotEqual(s,y)
        self.assertEqual(y,"use the key to open the door and then get to the goal")

    def test_source_rewriter_would_not_be_an_original_observation(self):
        changed=SOURCE.replace('"open the door"','"use the key to open the door and then get to the goal"')
        with self.assertRaisesRegex(RuntimeError,"AC28_ORIGINAL_UNLOCK_PUBLIC_MISSION_CHANGED"):
            a.original_missions(changed,YGG)

    def test_removal_of_native_mission_guard_is_not_same_frozen_actor(self):
        changed=YGG.replace('raise ValueError("R10_PUBLIC_MISSION")','pass')
        with self.assertRaisesRegex(RuntimeError,"AC28_ORIGINAL_MISSION_GUARD_NO_LONGER_CONFLICTS"):
            a.original_missions(SOURCE,changed)

    def test_archived_provenance_fails_closed_without_error_marker(self):
        with self.assertRaisesRegex(RuntimeError,"AC28_BLOCKED_SOURCE_EVIDENCE_NOT_AUTHENTIC"):
            a.archived_blocked(b'{"scientific_first_use":false}')
        r={"schema":"itd02.ac28.original-unlock-public-transfer-development.v1",
           "classification":"AC28_SOURCE_OR_PROTOCOL_BLOCKED__NO_SCIENCE",
           "scientific_first_use":False,"error_type":"ValueError",
           "error":"R10_PUBLIC_MISSION","trace_tail":["r10/public_adapter.py","R10_PUBLIC_MISSION"]}
        self.assertEqual(len(a.archived_blocked(json.dumps(r).encode())),64)
        r["error"]="FORGED_SUCCESS"
        with self.assertRaisesRegex(RuntimeError,"AC28_BLOCKED_SOURCE_EVIDENCE_NOT_AUTHENTIC"):
            a.archived_blocked(json.dumps(r).encode())

    def test_no_source_interaction_or_goal_score_authorized(self):
        self.assertEqual(a.OUTCOME,"AC28_PUBLIC_MISSION_INCOMPATIBLE__TARGET_TRANSFER_NOT_TESTED")
        self.assertEqual(a.ORIGINAL_AC28_FAILED_RUN,40844398914)
        self.assertEqual(a.SOURCE_COMMIT,"7f5853792ea7f04f75614661006d87fcf949f26d")
        self.assertEqual(a.YGG_COMMIT,"770244b04d011466458b2335d3951daf7653dc8f")

if __name__=="__main__":unittest.main()
