#!/usr/bin/env python3
"""TW5 development-only independent signature/catalog integrity tests."""
import hashlib
import hmac
import unittest
from tw5_synthetic_owner_catalog import (
    ACTOR, PLACE, ROLE, SCHEMA, SOURCE, DOMAIN, canon, valid_id,
    verify_synthetic_catalog, check_synthetic_destination,
)
KEY = b"TW5-LOCAL-NONOWNER-TEST-KEY-DO-NOT-DEPLOY-00"

def fixture():
    return {"schema": SCHEMA, "source_commit": SOURCE,
            "run_id": "run:development-1", "world_id": "world:development-1",
            "actor": "npc:0", "destinations": ["location:0", "location:1"],
            "max_actions": 3, "audience": ROLE}

def seal(d, key=KEY):
    return hmac.new(key, DOMAIN + canon(d), hashlib.sha256).hexdigest()

def verify(d=None, *, key=KEY, run="run:development-1", world="world:development-1",
           signature=None):
    d = fixture() if d is None else d
    return verify_synthetic_catalog(d, seal(d) if signature is None else signature,
                                    dev_owner_key=key, run_id=run, world_id=world)

class SyntheticTW5(unittest.TestCase):
    def reject(self, text, fn):
        with self.assertRaisesRegex(ValueError, text):
            fn()

    def test_01_valid_dev_fixture_is_never_owner_authorized(self):
        z=verify()
        self.assertFalse(z["source_owner_authenticated"])
        self.assertFalse(z["owner_action_dispatch_authorized"])
        self.assertFalse(z["fsa_first_use"])
        self.assertEqual(z["destinations"], ("location:0","location:1"))

    def test_02_membership_has_no_original_dispatch(self):
        z=check_synthetic_destination(verify(), actor="npc:0", destination="location:1")
        self.assertFalse(z["source_executed"])
        self.assertFalse(z["budget_reserved"])

    def test_03_altered_original_source_denied(self):
        d=fixture();d["source_commit"]="0"*40
        self.reject("SOURCE_IDENTITY",lambda:verify(d))

    def test_04_replay_wrong_run_denied(self):
        self.reject("SCOPE_MISMATCH",lambda:verify(run="run:development-2"))

    def test_05_replay_wrong_world_denied(self):
        self.reject("SCOPE_MISMATCH",lambda:verify(world="world:development-2"))

    def test_06_bad_signature_denied(self):
        self.reject("SEAL_MISMATCH",lambda:verify(signature="0"*64))

    def test_07_wrong_test_key_denied(self):
        self.reject("SEAL_MISMATCH",lambda:verify(key=b"Y"*40))

    def test_08_unsupported_extra_hidden_route_rejected(self):
        d=fixture();d["hidden_route"]=["location:2"]
        self.reject("EXACT_FIELDS",lambda:verify(d))

    def test_09_noncanonical_location_rejected(self):
        d=fixture();d["destinations"]=["loc:market"]
        self.reject("PUBLIC_LOCATIONS",lambda:verify(d))

    def test_10_location_index_over_js_safe_rejected(self):
        d=fixture();d["destinations"]=["location:9007199254740992"]
        self.reject("PUBLIC_LOCATIONS",lambda:verify(d))

    def test_11_leading_zero_rejected(self):
        d=fixture();d["destinations"]=["location:00"]
        self.reject("PUBLIC_LOCATIONS",lambda:verify(d))

    def test_12_duplicate_catalog_entry_rejected(self):
        d=fixture();d["destinations"]=["location:0","location:0"]
        self.reject("CANONICAL_DESTINATIONS",lambda:verify(d))

    def test_13_out_of_order_entries_rejected(self):
        d=fixture();d["destinations"]=["location:1","location:0"]
        self.reject("CANONICAL_DESTINATIONS",lambda:verify(d))

    def test_14_arbitrary_actor_rejected(self):
        d=fixture();d["actor"]="npc:ada"
        self.reject("ACTOR_ID",lambda:verify(d))

    def test_15_unknown_destination_rejected(self):
        self.reject("DESTINATION_NOT_PUBLIC",lambda:check_synthetic_destination(
            verify(),actor="npc:0",destination="location:3"))

    def test_16_other_actor_rejected(self):
        self.reject("ACTOR_CUSTODY",lambda:check_synthetic_destination(
            verify(),actor="npc:1",destination="location:0"))

    def test_17_boolean_budget_rejected(self):
        d=fixture();d["max_actions"]=True
        self.reject("ACTION_LIMIT",lambda:verify(d))

    def test_18_no_key_rejected(self):
        self.reject("EXTERNAL_TEST_KEY",lambda:verify(key=b""))

    def test_19_signature_format_denied(self):
        self.reject("SEAL_FORMAT",lambda:verify(signature="abcdef"))

    def test_20_syntactic_original_ids(self):
        self.assertTrue(valid_id("npc:0",ACTOR))
        self.assertTrue(valid_id("location:0",PLACE))
        self.assertFalse(valid_id("npc:ada",ACTOR))
        self.assertFalse(valid_id("loc:market",PLACE))

    def test_21_no_action_consumption_on_repeated_validation(self):
        a=verify()
        x=check_synthetic_destination(a,actor="npc:0",destination="location:0")
        y=check_synthetic_destination(a,actor="npc:0",destination="location:0")
        self.assertEqual(x,y)
        self.assertFalse(x["budget_reserved"])

    def test_22_world_binding_cannot_be_retagged_with_same_signature(self):
        d=fixture();proof=seal(d);d["world_id"]="world:development-2"
        self.reject("SEAL_MISMATCH",lambda:verify(d,world="world:development-2",signature=proof))

if __name__ == "__main__":
    unittest.main()
