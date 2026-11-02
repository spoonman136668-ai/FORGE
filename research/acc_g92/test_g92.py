"""G92 frozen synthetic analytical screen controls and exact-greedy guards."""
import unittest

import numpy as np
from threadpoolctl import threadpool_limits

from g92_microtree import (
    DEPTH, DRAFT_COST, HISTORIES, LOW_RANK, OUTPUT_TOKENS, SCHEMA,
    SEEDS, TARGET_SPEEDUP, VOCAB, WIDTHS, build_oracle, greedy_token,
    propose, reference_sequence, run_case, screen, svd_sketch, verify_tree,
)


class G92Guards(unittest.TestCase):
    def test_frozen_contract(self):
        self.assertEqual((VOCAB, LOW_RANK, DEPTH), (64, 8, 3))
        self.assertEqual(SEEDS, (9201, 9202, 9203))
        self.assertEqual(WIDTHS, (1, 2, 4))
        self.assertEqual((HISTORIES, OUTPUT_TOKENS), (16, 24))
        self.assertEqual((DRAFT_COST, TARGET_SPEEDUP), (.1, 1.15))

    def test_draft_is_deterministic_from_sketch_only(self):
        with threadpool_limits(limits=1):
            a, b, histories = build_oracle(SEEDS[0])
            draft_a, draft_b = svd_sketch(a, b)
            start = tuple(int(x) for x in histories[0])
            self.assertEqual(propose(draft_a, draft_b, start, 2),
                             propose(draft_a, draft_b, start, 2))
            self.assertEqual(len(propose(draft_a, draft_b, start, 2)), 2)

    def test_all_tree_nodes_charged(self):
        with threadpool_limits(limits=1):
            a, b, histories = build_oracle(SEEDS[0])
            da, db = svd_sketch(a, b)
            start = tuple(int(x) for x in histories[0])
            for width in WIDTHS:
                chunk, verified, drafted = verify_tree(a, b, da, db, start, width)
                self.assertEqual(verified, sum(width ** power for power in range(DEPTH+1)))
                self.assertEqual(drafted, sum(width ** power for power in range(DEPTH)))
                self.assertGreaterEqual(len(chunk), 1)
                self.assertLessEqual(len(chunk), 4)
                self.assertEqual(chunk[0], greedy_token(a, b, start))

    def test_exactness_and_full_144_case_screen(self):
        with threadpool_limits(limits=1):
            result = screen()
        self.assertEqual(result["schema"], SCHEMA)
        self.assertEqual(len(result["cases"]), 144)
        self.assertTrue(all(c["exact_reference_match"] for c in result["cases"]))
        self.assertTrue(all(c["emitted_tokens"] == OUTPUT_TOKENS for c in result["cases"]))
        self.assertTrue(all(np.isfinite(c["v_max_1p15x"]) for c in result["cases"]))
        self.assertEqual(result["actual_speedup"], "NOT_MEASURED")
        self.assertEqual(result["scientific_acceptance"], "NOT_GRANTED")
        self.assertEqual(result["gpu_model_evidence"], "NOT_RUN")
        self.assertIn(result["decision"], ("FEASIBILITY_ONLY", "NO_GO_ANALYTICAL"))


if __name__ == "__main__":
    unittest.main()
