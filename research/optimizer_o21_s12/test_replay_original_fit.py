"""O21-S13 strict source-role and public-observation guards. No simulator."""
import hashlib
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock
from research.optimizer_o21_s12 import replay_original_fit as replay

def example():
    return {
       "family":"empty","seed":31400,"action":2,"reward":0.0,
       "terminal":False,"start_sha256":"a"*64,"next_sha256":"b"*64,
       "before":{"X":4,"Y":4,"GoalX":6,"GoalY":6,"Direction":0,"FrontBlocked":False},
       "after":{"X":5,"Y":4,"GoalX":6,"GoalY":6,"Direction":0,"FrontBlocked":False}
    }

class FitOnlyRoleTests(unittest.TestCase):
    def test_real_selected_public_record_and_forward(self):
        a,b=replay.legal_record(example())
        self.assertEqual((a["x"],b["x"],a["goal_x"]), (4,5,6))
    def test_illegal_goal_or_observation_or_future_action_rejected(self):
        bad=example()
        bad["before"]["private_goal"]=1
        with self.assertRaisesRegex(ValueError,"PUBLIC_FIELDS"):replay.legal_record(bad)
        bad=example()
        bad["after"]["GoalX"]=7
        with self.assertRaisesRegex(ValueError,"GOAL_DISCONTINUITY"):replay.legal_record(bad)
        bad=example()
        bad["action"]=7
        with self.assertRaisesRegex(ValueError,"ILLEGAL_OR_UNEXECUTED"):replay.legal_record(bad)
        bad=example()
        bad["seed"]=33400
        with self.assertRaisesRegex(ValueError,"PROTECTED_OR_UNKNOWN"):replay.legal_record(bad)
    def test_original_dev_trailing_fragment_is_never_parsed(self):
        # Fake original provider with a correctly formed FIT array followed by
        # *malformed* private/DEV JSON. Only FIT may be decoded.
        raw=('{"FIT_original_public_experiences":'+json.dumps([example()],sort_keys=True)
             +',"DEV_original_public_traces":[this is intentionally not JSON}').encode()
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"original.zip"
            with zipfile.ZipFile(p,"w",compression=zipfile.ZIP_DEFLATED) as z:
                z.writestr("process-a.json",raw)
            with (mock.patch.object(replay,"EXPECTED_PROVIDER_SHA",hashlib.sha256(p.read_bytes()).hexdigest()),
                  mock.patch.object(replay,"SOURCE_ROWS",1),
                  mock.patch.object(replay,"EXPECTED_FAMILIES",{"empty":1})):
                rows,sha=replay.only_original_fit(p)
                self.assertEqual(len(rows),1)
                self.assertEqual(len(sha),64)
            with self.assertRaisesRegex(ValueError,"PROVIDER_SHA"):
                replay.only_original_fit(p)
    def test_wrong_original_zip_rejected_without_dev_read(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"corrupt.zip"
            p.write_bytes(b"unverified external artifact")
            with self.assertRaisesRegex(ValueError,"PROVIDER_SHA"):
                replay.only_original_fit(p)

if __name__=="__main__":unittest.main()
