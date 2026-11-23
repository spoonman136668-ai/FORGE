"""Third F139 native-development lane: source-bound admission, no science grant."""
import base64
import hashlib
import hmac
import json
import unittest

from f139.nci04_native_contract import parse_intent, NativeContractError, digest
from f139.nci04_native_worker import commands_for, COMMANDS
from f139.nci04_autonomy_feed import (
    POLICY_SCHEMA, TITLE_PREFIX, NATIVE_FEED_LANES,
    HYBRID_FEED_LANES, inspect_policy, NativeFeedDenied,
)
from f139.verify_ticket import signature, receipt, Untrusted

FORGE="a"*40
HEAD="b"*40
TREE="c"*40
SECRET="owner-unit-test-hmac-never-deploy-0000000000000000000"


def hybrid_intent(path="scripts/native_qualified_policy.py",repo="spoonman136668-ai/TTT-Hybrid-Lab",first_use=False):
    before=b"def after_action():\n    return None\n"
    after=b"def after_action():\n    return 1\n"
    return {
        "schema":"forge.f139.nci04.native-candidate-intent.v1",
        "controller_source_sha":FORGE,"lane":"TTT-Hybrid",
        "target_repository":repo,"target_commit":HEAD,
        "target_tree_sha":TREE,"dependency_sha256":"d"*64,
        "qualification_harness_sha256":"e"*64,
        "training_config_sha256":"f"*64,
        "toolchain_identity":"python3.11.11",
        "suite_identity_sha256":"1"*64,"path":path,
        "before_sha256":digest(before),"after_sha256":digest(after),
        "after_base64":base64.b64encode(after).decode(),
        "worker_mode":"isolated-candidate-only",
        "scientific_first_use":first_use,"paid_api_calls":0,
        "accepted_ref_mutations":0,"optimizer_policy_mutations":0,
        "protected_holdouts_accessed":0,
    }


def parse(data):
    return parse_intent(json.dumps(data,sort_keys=True,separators=(",",":")).encode(),
                        protected_main=FORGE,target_commit=HEAD,
                        target_tree_sha=TREE)


class HybridNativeOwnerAdmissionTests(unittest.TestCase):
    def test_hybrid_is_a_distinct_real_native_source_candidate_not_a_fake_research_run(self):
        c=parse(hybrid_intent())
        self.assertEqual(c.lane,"TTT-Hybrid")
        self.assertEqual(len(c.qualification_key),64)
        self.assertEqual(c.path,"scripts/native_qualified_policy.py")
        self.assertEqual(commands_for(c),COMMANDS["TTT-Hybrid"])
        command=commands_for(c)
        self.assertEqual(command[1],("python","-B","-m","pytest","-q"))
        self.assertNotIn("native_p34_mountaincar_reward_ppo_dev.py",str(command))
        self.assertNotIn("workflow_dispatch",str(command))
        other=parse(hybrid_intent(path="tests/test_native_action_source.py"))
        self.assertNotEqual(other.qualification_key,c.qualification_key)

    def test_hybrid_source_and_authority_negative_controls(self):
        for field,value in (
            ("target_repository","spoonman136668-ai/Wingless"),
            ("toolchain_identity","go1.25.0"),
            ("worker_mode","original-scientific-training"),
            ("scientific_first_use",True),
            ("accepted_ref_mutations",1),
            ("paid_api_calls",1),
            ("protected_holdouts_accessed",1),
        ):
            bad=hybrid_intent();bad[field]=value
            with self.subTest(field=field),self.assertRaises(NativeContractError):
                parse(bad)
        for path in (
            ".github/workflows/bypass.yml","scripts/native/../bypass.py",
            "scripts/bypass.py","tests/test_untrusted.py",
            "scripts/native_trial.sh","scripts/native_malicious.py/../no.py",
            "science/accepted_model.py","../scripts/native_bad.py",
        ):
            with self.subTest(path=path),self.assertRaises(NativeContractError):
                parse(hybrid_intent(path=path))

    def test_signed_hybrid_native_ticket_never_becomes_legacy_science_or_d2k(self):
        ticket="f139-nci04-i1150-aaaaaaaaaaaa-01234567"
        sig=signature(SECRET,ticket,"TTT-Hybrid",FORGE,"1")
        self.assertRegex(sig,r"^[a-f0-9]{64}$")
        with self.assertRaisesRegex(Untrusted,"HYBRID_NATIVE_SIGNED_INTENT_REQUIRED"):
            signature(SECRET,"f139-legacy-hybrid-001","TTT-Hybrid",FORGE,"1")
        with self.assertRaisesRegex(Untrusted,"HYBRID_NATIVE_SIGNED_INTENT_REQUIRED"):
            signature(SECRET,"f139-d2k-i1150-aaaaaaaaaaaa-01234567",
                      "TTT-Hybrid",FORGE,"1",
                      issue_number="1150",issue_id="9150",
                      body_sha256="f"*64,target_package="./planner")
        i={"key":SECRET,"ticket":ticket,"lane":"TTT-Hybrid",
           "source_sha":FORGE,"epoch":"1","signature":sig,
           "repository":"spoonman136668-ai/FORGE",
           "ref":"refs/heads/main","event":"workflow_dispatch",
           "head_sha":FORGE,"run_attempt":"1","run_id":"100001",
           "os":"windows-latest"}
        with self.assertRaisesRegex(Untrusted,"HYBRID_NATIVE_RECEIPT_REQUIRED"):
            receipt(i,b'{"schema":"forge.model-free.two-lane-untested-advisory.v1"}')

    def test_owner_policy_preserves_two_lane_and_requires_hybrid_explicit_optin(self):
        def policy(lanes):
            data={"schema":POLICY_SCHEMA,"enabled":True,"source_sha":FORGE,
                "title_prefix":TITLE_PREFIX,"lanes":list(lanes),
                "max_issue_creations_per_cycle":2,
                "require_owner_authored_pr":True,
                "require_single_head_commit_delta":True,
                "require_single_allowed_source_file":True,
                "scientific_first_use":False,"paid_model_calls":0,
                "accepted_ref_mutations":0,"new_controller":False,
                "new_scheduler":False,"new_queue":False}
            return {"number":807,"state":"open","user":{"login":"spoonman136668-ai"},
                    "author_association":"OWNER","body":json.dumps(data)}
        self.assertEqual(inspect_policy(policy(NATIVE_FEED_LANES),FORGE)["lanes"],
                         list(NATIVE_FEED_LANES))
        self.assertEqual(inspect_policy(policy(HYBRID_FEED_LANES),FORGE)["lanes"],
                         list(HYBRID_FEED_LANES))
        with self.assertRaises(NativeFeedDenied):
            inspect_policy(policy(("TTT-Hybrid",)),FORGE)
        with self.assertRaises(NativeFeedDenied):
            inspect_policy(policy((*HYBRID_FEED_LANES,"Yggdrasil")),FORGE)
        with self.assertRaises(NativeFeedDenied):
            inspect_policy(policy(HYBRID_FEED_LANES), "b"*40)


if __name__=="__main__":
    unittest.main()
