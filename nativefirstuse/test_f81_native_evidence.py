"""F81: genuine pinned FIT metadata never upgrades repo-local activity to science."""
import sys
from pathlib import Path
import unittest
from copy import deepcopy

sys.path.insert(0,str(Path(__file__).resolve().parent))
from f81_native_evidence import assess,Blocked,SCHEMA,PINS

def fixture():
    lanes=[]
    archives={}
    for lane in ("Wingless","Yggdrasil"):
        lanes.append({
            "lane":lane,"repository":"spoonman136668-ai/"+lane,
            "main_sha":"a"*40,"active_research_head":"b"*40,
            "last_continuation_run_confirmed":38830000001,
            "repo_local_research_workflow_confirmed":True,
            "full_original_seed_lease_ledger_independently_observed":False,
            "current_scientific_owner_independently_authorized":False,
            "prospective_original_firstuse_available":False,
        })
        pin=PINS[lane]
        archives[lane]={"artifacts":[{
            "id":pin["artifact"],"digest":pin["digest"],"expired":False,
            "workflow_run":{"id":pin["run"]}}]}
    live={"schema":"forge.f74.real-two-lane-native-intake.readonly.v1",
        "lanes":lanes,"private_rbackup_restoration_qualified":False,
        "cloudflare_time_travel_only_is_independent_backup":False,
        "atomic_live_original_firstuse_claim_qualified":False,
        "native_worker_execution_permit_issued":False,
        "new_protected_originals_dispatched":0}
    return live,archives

class TestF81(unittest.TestCase):
    def test_valid_two_lane_pinned_source_only_does_not_grant_original(self):
        live,archive=fixture()
        data=assess(live,archive)
        self.assertEqual(data["schema"],SCHEMA)
        self.assertTrue(data["two_live_lanes_verified"])
        self.assertTrue(data["two_real_fit_archive_metadata_identities_verified"])
        self.assertEqual(data["fresh_independently_accepted_originals"],0)
        for field in ("policy_training_qualified","dream_rsi_pareto_promoted",
          "cloudflare_firstuse_permit_issued","new_original_dispatched",
          "scientific_execution_authorized"):
            self.assertIs(data[field],False)
        self.assertEqual({x["lane"] for x in data["lane_evidence"]},
                         {"Wingless","Yggdrasil"})

    def test_missing_duplicate_and_swapped_lanes_are_denied(self):
        for name in ("missing","duplicate","swapped_repo","missing_archive"):
            with self.subTest(name=name):
                l,a=fixture()
                if name=="missing":l["lanes"]=l["lanes"][:1]
                if name=="duplicate":l["lanes"][1]=deepcopy(l["lanes"][0])
                if name=="swapped_repo":l["lanes"][0]["repository"]="spoonman136668-ai/Yggdrasil"
                if name=="missing_archive":del a["Wingless"]
                with self.assertRaises(Blocked):assess(l,a)

    def test_fit_digest_expiry_or_run_drift_denies(self):
        for lane in ("Wingless","Yggdrasil"):
            for field in ("digest","id","expired","run"):
                with self.subTest(lane=lane,field=field):
                    l,a=fixture();row=a[lane]["artifacts"][0]
                    if field=="digest":row["digest"]="sha256:"+"0"*64
                    if field=="id":row["id"]=0
                    if field=="expired":row["expired"]=True
                    if field=="run":row["workflow_run"]["id"]+=1
                    with self.assertRaises(Blocked):assess(l,a)

    def test_source_or_claimed_authority_drift_does_not_escalate(self):
        for field,val in (
            ("current_scientific_owner_independently_authorized",True),
            ("full_original_seed_lease_ledger_independently_observed",True),
            ("prospective_original_firstuse_available",True),
            ("repo_local_research_workflow_confirmed",False),
            ("main_sha","not-a-sha"),
            ("active_research_head","bad"),
            ("last_continuation_run_confirmed",0)):
            with self.subTest(field=field):
                l,a=fixture();l["lanes"][0][field]=val
                with self.assertRaises(Blocked):assess(l,a)

    def test_backup_time_travel_and_fake_worker_admission_drift_denied(self):
        for field,value in (
            ("private_rbackup_restoration_qualified",True),
            ("cloudflare_time_travel_only_is_independent_backup",True),
            ("atomic_live_original_firstuse_claim_qualified",True),
            ("native_worker_execution_permit_issued",True),
            ("new_protected_originals_dispatched",1)):
            with self.subTest(field=field):
                l,a=fixture();l[field]=value
                with self.assertRaises(Blocked):assess(l,a)

if __name__=="__main__":unittest.main()
