"""Synthetic-only falsification of frozen Transformer encoder-cache equivalence."""
import unittest
from pathlib import Path

import l9_cached_encoder_parity as p


class CachedEncoderParityTests(unittest.TestCase):
    def test_exact_immutable_original_source_identity(self):
        p.require_frozen_source(Path(__file__).resolve().parent)
        self.assertEqual(len(p.FROZEN_MODEL_BLOB), 40)
        self.assertEqual(len(p.FROZEN_SELECT_BLOB), 40)

    def test_genuine_synthetic_token_and_logit_parity(self):
        receipt = p.synthetic_equivalence(steps=12)
        self.assertEqual(len(receipt["test_cases"]), 3)
        self.assertFalse(receipt["checkpoint_weights_loaded"])
        self.assertFalse(receipt["train_select_audit_test_loaded"])
        self.assertFalse(receipt["scientific_cost_pareto_qualified"])
        for case in receipt["test_cases"]:
            self.assertTrue(case["exact_token_equivalence"])
            self.assertEqual(case["old_encoder_invocations"],
                             case["generated_tokens"])
            self.assertEqual(case["cached_encoder_invocations"], 1)
            self.assertLessEqual(case["max_abs_logit_difference"], 2e-6)

    def test_rejects_training_mode_and_invalid_inputs(self):
        import torch
        import l9_model_suite as m
        net = m.build_transformer_model()
        src = torch.tensor([[2, 5, 8]], dtype=torch.long)
        with self.assertRaisesRegex(ValueError, "REQUIRES_EVAL"):
            p.cached_encoder_greedy(net, src, max_steps=5)
        net.eval()
        for bad in (0, 514, True):
            with self.subTest(cap=bad), self.assertRaisesRegex(
                    ValueError, "BAD_STEP_CAP"):
                p.cached_encoder_greedy(net, src, max_steps=bad)
        with self.assertRaisesRegex(ValueError, "REQUIRES_SINGLE_GRAPH"):
            p.cached_encoder_greedy(net, src.repeat(2, 1), max_steps=3)
        with self.assertRaisesRegex(ValueError, "REQUIRES_UNPADDED_SOURCE"):
            p.cached_encoder_greedy(net, torch.tensor([[2, 256]]), max_steps=3)

    def test_early_eos_preserved(self):
        import torch
        import l9_model_suite as m
        torch.manual_seed(17)
        net = m.build_transformer_model().eval()
        with torch.no_grad():
            net.output.weight.zero_()
            net.output.bias.zero_()
            net.output.bias[m.EOS] = 100.0
        src = torch.tensor([[3, 5, 7]], dtype=torch.long)
        with torch.inference_mode():
            original = net.greedy(src, max_steps=8)
            cached = p.cached_encoder_greedy(net, src, max_steps=8)
        self.assertEqual(original.shape[1], 1)
        self.assertTrue(torch.equal(original, cached))
        self.assertEqual(original.item(), m.EOS)

    def test_no_benchmark_or_saved_checkpoint_access_in_parity_code(self):
        code = (Path(__file__).resolve().parent /
                "l9_cached_encoder_parity.py").read_text(encoding="utf-8")
        for forbidden in (
            "torch.load(", "load_state_dict(", "load_train_select(",
            "load_audit(", "subprocess.", "requests.", "WebNLG",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, code)


if __name__ == "__main__":
    unittest.main()
