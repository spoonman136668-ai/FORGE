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


if __name__ == "__main__":
    unittest.main()
