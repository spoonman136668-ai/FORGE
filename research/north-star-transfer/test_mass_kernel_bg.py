"""F124-BG: synthetic-only tests of immutable T1 kernel boundaries.

No held-out family, protected DEV or original scientific source is generated
or accessed. Passing tests are engineering evidence only.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

FILE = Path(__file__).with_name("20261018-mass-learned-kernel.py")
spec = importlib.util.spec_from_file_location("mass_kernel_f124bg", FILE)
kernel = importlib.util.module_from_spec(spec)
spec.loader.exec_module(kernel)


def synthetic_task(masks: bytes):
    fit_x = [((i * 4009 + 71) & 65535) for i in range(40)]
    check_x = [((i * 6221 + 103) & 65535) for i in range(8)]
    fit = [(x, kernel.forward(x, masks)) for x in fit_x]
    check = [(x, kernel.forward(x, masks)) for x in check_x]
    return fit, check


class BoundedSyntheticKernelTests(unittest.TestCase):
    def test_exact_bijection_across_full_16bit_domain(self):
        for masks in (bytes(4), bytes((0x35, 0x9c, 0x6a, 0xc3)),
                      bytes((0xff, 0x00, 0xaa, 0x55))):
            seen = bytearray(65536)
            for value in range(65536):
                encoded = kernel.forward(value, masks)
                self.assertGreaterEqual(encoded, 0)
                self.assertLess(encoded, 65536)
                self.assertEqual(seen[encoded], 0, "non-bijective collision")
                seen[encoded] = 1
                self.assertEqual(kernel.inverse(encoded, masks), value)
            self.assertEqual(sum(seen), 65536)

    def test_check_observations_never_select_fit_weights(self):
        fit, check = synthetic_task(bytes((0x35, 0x9c, 0x6a, 0xc3)))
        adversarial_check = [(x, y ^ 65535) for x, y in check]
        weights_a, receipt_a = kernel.fit_public(fit, check)
        weights_b, receipt_b = kernel.fit_public(fit, adversarial_check)
        self.assertEqual(weights_a, weights_b)
        self.assertEqual(receipt_a["public_FIT_bit_errors"],
                         receipt_b["public_FIT_bit_errors"])
        self.assertEqual(receipt_a["public_CHECK_bit_errors"],
                         kernel.errors(check, weights_a))
        self.assertEqual(receipt_b["public_CHECK_bit_errors"],
                         kernel.errors(adversarial_check, weights_b))
        self.assertEqual(receipt_a["public_forward_evaluations"], 2608)
        self.assertEqual(receipt_b["public_forward_evaluations"], 2608)
        self.assertEqual(receipt_a["parameter_bits"], 32)
        for receipt in (receipt_a, receipt_b):
            self.assertIs(receipt["complete_task_memory_qualified"], False)
            self.assertIs(receipt["full_train_amortized_compute_qualified"], False)
            self.assertIs(receipt["independent_OOD_result"], False)

    def test_shared_prior_is_training_only_and_cost_accounted(self):
        task = synthetic_task(bytes((0x35, 0x9c, 0x6a, 0xc3)))
        single_weights, _ = kernel.fit_public(*task)
        prior, receipt = kernel.learned_prior([task, task])
        self.assertEqual(prior, single_weights)
        self.assertEqual(len(prior), 4)
        self.assertEqual(receipt["public_training_task_count"], 2)
        self.assertEqual(receipt["training_forward_evaluations"], 5216)
        self.assertIs(receipt["training_temporary_memory_not_qualified"], True)

    def test_invalid_inputs_fail_closed(self):
        with self.assertRaises(ValueError):
            kernel.forward(-1, bytes(4))
        with self.assertRaises(ValueError):
            kernel.forward(65536, bytes(4))
        with self.assertRaises(ValueError):
            kernel.inverse(12, b"123")
        with self.assertRaises(ValueError):
            kernel.forward(12.0, bytes(4))
        with self.assertRaises(ValueError):
            kernel.errors([(1, -1)], bytes(4))
        fit, check = synthetic_task(bytes(4))
        with self.assertRaises(ValueError):
            kernel.fit_public(fit[:-1], check)
        with self.assertRaises(ValueError):
            kernel.fit_public(fit, check[:-1])
        with self.assertRaises(ValueError):
            kernel.learned_prior([])
        with self.assertRaises(ValueError):
            kernel.learned_prior([((fit), (check))] * 193)


if __name__ == "__main__":
    unittest.main()
