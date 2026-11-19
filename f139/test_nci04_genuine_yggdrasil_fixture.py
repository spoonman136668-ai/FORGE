"""Real pinned Yggdrasil source-only variants: immutable native behavior controls.

These imported fixtures are never used by a production owner. They are source
tests of two finite opt-in recipes, not scientific acceptance or dispatch.
"""
import hashlib
import importlib
import random
import unittest
from fractions import Fraction
from pathlib import Path

from f139.nci04_model_free_grammar import method_for

ORIGINAL_SHA256 = "5e6f8a8bfd635c0117fe864f7eb33988b6db319b40dacb29ba44d5a6e2beabac"
FIXTURES = (
    ("f139.nci04_genuine_yggdrasil_p1_fixture", 1,
     "d069dbfbbf4f620773fbcb614428b37edf92a33ed2dd2811746494defbded5aa"),
    ("f139.nci04_genuine_yggdrasil_p2_fixture", 2,
     "e376eaa2b7d4b574680ae4c4883e37c2b070c1898e918c6e71b005c39c1aebd9"),
)


class GenuineSourceTests(unittest.TestCase):
    def test_exact_original_bytes_preserved_in_each_fixture(self):
        for name, prior, expected in FIXTURES:
            with self.subTest(prior=prior):
                module = importlib.import_module(name)
                source = Path(module.__file__).read_bytes()
                added = method_for(prior).encode("ascii")
                self.assertEqual(len(source), 7439)
                self.assertEqual(hashlib.sha256(source).hexdigest(), expected)
                self.assertEqual(source.count(added), 1)
                original = source.replace(added, b"", 1)
                self.assertEqual(len(original), 6067)
                self.assertEqual(hashlib.sha256(original).hexdigest(),
                                 ORIGINAL_SHA256)

    def test_observation_reward_cost_and_checkpoint_preserved(self):
        rng = random.Random(0xF139)
        variants = [importlib.import_module(n).PublicCausalCells
                    for n, _, _ in FIXTURES]
        for retained in (False, True):
            for _ in range(128):
                address = rng.randrange(9 if retained else 7)
                cells = [variant() for variant in variants]
                for action in (0, 1):
                    for _ in range(rng.randrange(1, 35)):
                        result = rng.randrange(2)
                        for cell in cells:
                            cell.observe(address, action, result,
                                         retained=retained)
                baseline = cells[0].snapshot()
                self.assertEqual(cells[1].snapshot(), baseline)
                self.assertEqual(cells[0].choose(address, retained=retained),
                                 cells[1].choose(address, retained=retained))
                idx = cells[0]._address(address, retained)
                (f0, s0), (f1, s1) = cells[0]._counts[idx]
                n0, n1 = f0 + s0, f1 + s1
                cost0, cost1 = rng.randrange(30), rng.randrange(30)
                reward = rng.randrange(1, 40)
                for cell, prior in zip(cells, (1, 2)):
                    v0 = Fraction(s0 + prior, n0 + 2 * prior) * reward - cost0
                    v1 = Fraction(s1 + prior, n1 + 2 * prior) * reward - cost1
                    expected = 0 if v0 > v1 else (1 if v1 > v0 else None)
                    method = getattr(cell,
                                     f"choose_posterior_public_cost_p{prior}")
                    self.assertEqual(method(address, cost0, cost1,
                                            reward_value=reward,
                                            retained=retained), expected)
                    self.assertEqual(cell.snapshot(), baseline)
                    self.assertEqual(type(cell).restore(baseline).snapshot(),
                                     baseline)

    def test_public_evidence_abstention_and_invalid_inputs(self):
        for name, prior, _ in FIXTURES:
            with self.subTest(prior=prior):
                cells = importlib.import_module(name).PublicCausalCells()
                decision = getattr(cells,
                                   f"choose_posterior_public_cost_p{prior}")
                self.assertIsNone(decision(0, 0, 0))
                cells.observe(0, 0, 1)
                self.assertIsNone(decision(0, 0, 0))
                before = cells.snapshot()
                for a, b in ((True, 0), (0, True), (-1, 0),
                             (0, 65536)):
                    with self.assertRaises(ValueError):
                        decision(0, a, b)
                with self.assertRaises(ValueError):
                    decision(0, 0, 0, reward_value=0)
                self.assertEqual(cells.snapshot(), before)



    def test_h32_real_source_grammar_exactly_matches_frozen_native_fixture(self):
        """A finite code generator is not an independently qualified executor."""
        from f139.nci04_model_free_grammar import generate

        p1 = Path(importlib.import_module(FIXTURES[0][0]).__file__).read_bytes()
        p2 = Path(importlib.import_module(FIXTURES[1][0]).__file__).read_bytes()
        original = p1.replace(method_for(1).encode("ascii"), b"", 1)
        self.assertEqual(len(original), 6067)
        self.assertEqual(hashlib.sha256(original).hexdigest(), ORIGINAL_SHA256)
        metadata = {
            "dependency_sha256": "d" * 64,
            "qualification_harness_sha256": "e" * 64,
            "suite_identity_sha256": "f" * 64,
            "training_config_sha256": "1" * 64,
            "frozen_split_sha256": "2" * 64,
        }
        plan = generate(
            controller_source_sha="49c7b15343bea3c201fb52b498d8c0f397384afe",
            target_commit="5e74f8db85b2f5839c42148c0dfba69a88b1a2c9",
            target_tree_sha="180008502f6bdfe5a06c3d0d6f47f941dd01f20b",
            frozen_source_sha256=ORIGINAL_SHA256, original=original,
            metadata=metadata, complete_history=[])
        self.assertEqual(plan["generated_recipe_count"], 2)
        self.assertEqual(len(plan["selected"]), 1)
        selected = plan["selected"][0]
        candidate = plan["source_by_candidate_id"][selected["candidate_identity"]]
        self.assertIn(candidate, (p1, p2))
        self.assertEqual(hashlib.sha256(candidate).hexdigest(),
                         selected["after_sha256"])
        self.assertEqual(plan["source_authentication"], "EXTERNAL_OWNER_REQUIRED")
        self.assertEqual(plan["history_authentication"],
                         "COMPLETE_ORIGINAL_LEDGER_REQUIRED")
        self.assertEqual(plan["qualification"], "NOT_RUN_NOT_ACCEPTED")
        for key in ("publication_authorized", "dispatch_authorized",
                    "scientific_first_use", "new_controller",
                    "new_scheduler", "new_queue"):
            self.assertIs(plan[key], False)

    def test_h32_native_intent_does_not_inherit_frozen_split_or_mechanism(self):
        """Negative cross-interface witness: identical worker key, distinct science lineage.

        Native V26 intent is *not* a qualified bridge for the model-free grammar:
        it omits frozen_split_sha256 and mechanism_sha256. The caller must secure
        separately signed original-actor source, mechanism, split and custody.
        No issue, provider, owner, ledger, environment or holdout is accessed.
        """
        import base64
        import json
        from f139.nci04_model_free_frontier import verify_proposal
        from f139.nci04_native_contract import FIELDS, SCHEMA, parse_intent
        source = Path(importlib.import_module(FIXTURES[0][0]).__file__).read_bytes()
        original = source.replace(method_for(1).encode("ascii"), b"", 1)
        proposal = {
            "lane": "Yggdrasil",
            "controller_source_sha": "49c7b15343bea3c201fb52b498d8c0f397384afe",
            "target_commit": "5e74f8db85b2f5839c42148c0dfba69a88b1a2c9",
            "target_tree_sha": "180008502f6bdfe5a06c3d0d6f47f941dd01f20b",
            "path": "yggdrasil/public_causal_cells.py",
            "before_sha256": hashlib.sha256(original).hexdigest(),
            "after_sha256": hashlib.sha256(source).hexdigest(),
            "mechanism_sha256": "a" * 64,
            "dependency_sha256": "d" * 64,
            "qualification_harness_sha256": "e" * 64,
            "suite_identity_sha256": "f" * 64,
            "training_config_sha256": "1" * 64,
            "toolchain_identity": "python3.11.11",
            "frozen_split_sha256": "2" * 64,
            "scientific_first_use": False,
            "protected_holdouts_accessed": 0,
            "paid_model_calls": 0,
            "accepted_ref_mutations": 0,
            "optimizer_policy_mutations": 0,
        }
        altered = dict(proposal, frozen_split_sha256="3" * 64,
                       mechanism_sha256="b" * 64)
        first = verify_proposal(proposal, proposal["controller_source_sha"])
        changed = verify_proposal(altered, altered["controller_source_sha"])
        self.assertNotEqual(first["candidate_identity"],
                            changed["candidate_identity"])
        self.assertNotIn("frozen_split_sha256", FIELDS)
        self.assertNotIn("mechanism_sha256", FIELDS)

        def legacy_native_key(row):
            native = {
                "schema": SCHEMA,
                "controller_source_sha": row["controller_source_sha"],
                "lane": "Yggdrasil",
                "target_repository": "spoonman136668-ai/Yggdrasil",
                "target_commit": row["target_commit"],
                "target_tree_sha": row["target_tree_sha"],
                "dependency_sha256": row["dependency_sha256"],
                "qualification_harness_sha256":
                    row["qualification_harness_sha256"],
                "training_config_sha256": row["training_config_sha256"],
                "toolchain_identity": row["toolchain_identity"],
                "suite_identity_sha256": row["suite_identity_sha256"],
                "path": row["path"],
                "before_sha256": row["before_sha256"],
                "after_sha256": row["after_sha256"],
                "after_base64": base64.b64encode(source).decode("ascii"),
                "worker_mode": "isolated-candidate-only",
                "scientific_first_use": False,
                "paid_api_calls": 0,
                "accepted_ref_mutations": 0,
                "optimizer_policy_mutations": 0,
                "protected_holdouts_accessed": 0,
            }
            self.assertEqual(set(native), FIELDS)
            intent = json.dumps(native, sort_keys=True,
                                separators=(",", ":")).encode("ascii")
            parsed = parse_intent(
                intent, protected_main=row["controller_source_sha"],
                target_commit=row["target_commit"],
                target_tree_sha=row["target_tree_sha"])
            self.assertEqual(parsed.after_bytes, source)
            return parsed.qualification_key

        # Same legacy key for differing frozen scientific identity is a
        # negative compatibility result, NOT a cryptographic collision or GO.
        self.assertEqual(legacy_native_key(proposal),
                         legacy_native_key(altered))

if __name__ == "__main__":
    unittest.main()
