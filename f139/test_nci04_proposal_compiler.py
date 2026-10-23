"""Source-only proposal compiler tests; no owner identity, dispatch or science."""
import base64
import json
import unittest

from f139.nci04_native_contract import digest, parse_intent, NativeContractError
from f139.nci04_proposal_compiler import prepare_proposal, ProposalPreparationError


class TestProposalPreparation(unittest.TestCase):
    def args(self):
        return dict(
            controller_source_sha="a" * 40,
            lane="Wingless", target_commit="b" * 40,
            target_tree_sha="c" * 40,
            path="cognition/learned_state.go",
            before=b"package cognition\n\nconst State = 0\n",
            after=b"package cognition\n\nconst State = 1\n",
            dependency_sha256=digest(b"deps"),
            qualification_harness_sha256=digest(b"harness"),
            training_config_sha256=digest(b"training"),
            suite_identity_sha256=digest(b"suite"),
            toolchain_identity="go1.25.0",
        )

    def test_compiles_canonical_v1_proposal_without_authority(self):
        args = self.args()
        result = prepare_proposal(**args)
        issue = json.loads(result["issue_body"])
        raw = base64.b64decode(issue["intent_base64"], validate=True)
        candidate = parse_intent(raw, protected_main=args["controller_source_sha"],
                                 target_commit=args["target_commit"],
                                 target_tree_sha=args["target_tree_sha"])
        self.assertEqual(candidate.after_bytes, args["after"])
        self.assertEqual(candidate.qualification_key, result["qualification_key"])
        self.assertEqual(result["issue_body_sha256"], digest(result["issue_body"].encode()))
        self.assertFalse(result["eligible"])
        self.assertFalse(result["dispatch_authorized"])
        self.assertFalse(result["scientific_first_use"])
        self.assertTrue(result["owner_issue_required"])
        self.assertEqual(issue["scientific_first_use"], False)
        self.assertEqual(issue["paid_model_calls"], 0)
        self.assertEqual(result, prepare_proposal(**args))

    def test_rejects_unchanged_or_absent_source(self):
        args = self.args()
        with self.assertRaises(ProposalPreparationError):
            prepare_proposal(**{**args, "after": args["before"]})
        with self.assertRaises(ProposalPreparationError):
            prepare_proposal(**{**args, "before": b""})

    def test_fail_closed_on_paths_targets_and_identities(self):
        args = self.args()
        for update in (
            {"path": "../cognition/x.go"},
            {"path": "cognition/.hidden.go"},
            {"path": "scripts/foreign.py"},
            {"toolchain_identity": "go1.26.0"},
            {"target_tree_sha": "INVALID"},
            {"controller_source_sha": "x" * 40},
            {"qualification_harness_sha256": "0"},
            {"after": b"x" * 32769},
            {"lane": "Other"},
        ):
            with self.subTest(update=tuple(update)):
                with self.assertRaises((NativeContractError, ProposalPreparationError)):
                    prepare_proposal(**{**args, **update})

    def test_yggdrasil_proposal(self):
        args = self.args()
        args.update(lane="Yggdrasil", path="yggdrasil/memory.py",
                    toolchain_identity="python3.11.11",
                    before=b"x = 0\n", after=b"x = 1\n")
        data = prepare_proposal(**args)
        self.assertFalse(data["eligible"])
        self.assertIn('Yggdrasil', data["issue_body"])


if __name__ == "__main__":
    unittest.main()
