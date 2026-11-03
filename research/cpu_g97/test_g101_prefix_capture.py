"""Model-free G101 capture tests. No original checkpoint or protected data."""
import unittest
from research.cpu_g97.g101_prefix_capture import (
    PrefixCaptureError, capture_prefix_from_full_prefill, prefill_and_capture)


class Tensor:
    """Minimal GPT-2-like tensor with explicit view/clone backing identity."""
    allocations = 0

    def __init__(self, seq, *, width=1, backing=None, clone_alias=False):
        self.seq, self.width = seq, width
        self.shape = (1, 1, len(seq), width)
        self.backing = backing if backing is not None else object()
        self.clone_alias = clone_alias

    def numel(self):
        return len(self.seq) * self.width

    def element_size(self):
        return 4

    def data_ptr(self):
        return id(self.backing)

    def __getitem__(self, at):
        assert isinstance(at, tuple) and len(at) == 3 and at[0] is Ellipsis
        return Tensor(self.seq[at[-2]], width=self.width, backing=self.backing,
                      clone_alias=self.clone_alias)

    def detach(self):
        return self

    def clone(self):
        Tensor.allocations += 1
        return Tensor(list(self.seq), width=self.width,
                      backing=self.backing if self.clone_alias else None)


def past(length=7, layers=2, *, clone_alias=False):
    return tuple((Tensor(list(range(length)), clone_alias=clone_alias),
                  Tensor([100+i for i in range(length)], clone_alias=clone_alias))
                 for _ in range(layers))


class G101PrefixCaptureTests(unittest.TestCase):
    def setUp(self):
        Tensor.allocations = 0

    def test_compact_prefix_copy_isolated_from_source(self):
        src = past()
        saved = capture_prefix_from_full_prefill(src, 3, expected_bytes=48)
        self.assertEqual(len(saved), 2)
        self.assertEqual(Tensor.allocations, 4)
        for (key, value), (old_key, old_value) in zip(saved, src):
            self.assertEqual(key.seq, old_key.seq[:3])
            self.assertEqual(value.seq, old_value.seq[:3])
            self.assertNotEqual(key.data_ptr(), old_key.data_ptr())
            self.assertNotEqual(value.data_ptr(), old_value.data_ptr())
        src[0][0].seq[0] = -999
        self.assertEqual(saved[0][0].seq[0], 0)

    def test_budget_and_size_drift_rejected_before_copy(self):
        with self.assertRaisesRegex(PrefixCaptureError, "MEMORY_CAP_EXCEEDED"):
            capture_prefix_from_full_prefill(past(), 3, byte_limit=40)
        with self.assertRaisesRegex(PrefixCaptureError, "EXPECTED_BYTES_DRIFT"):
            capture_prefix_from_full_prefill(past(), 3, expected_bytes=40)
        self.assertEqual(Tensor.allocations, 0)

    def test_invalid_tree_and_prefix_fail_closed(self):
        for length in (0, -1, True, 9):
            with self.assertRaises(PrefixCaptureError):
                capture_prefix_from_full_prefill(past(), length)
        for tree in ([], (), [(Tensor([1]),)], [(Tensor([1]), Tensor([1, 2]))]):
            with self.assertRaises(PrefixCaptureError):
                capture_prefix_from_full_prefill(tree, 1)
        self.assertEqual(Tensor.allocations, 0)

    def test_prefix_independent_of_suffix(self):
        left = capture_prefix_from_full_prefill(past(9), 4)
        right = capture_prefix_from_full_prefill(past(12), 4)
        self.assertEqual([[t.seq for t in layer] for layer in left],
                         [[t.seq for t in layer] for layer in right])

    def test_clone_alias_rejected(self):
        with self.assertRaisesRegex(PrefixCaptureError, "UNSAFE_STORAGE_ALIAS"):
            capture_prefix_from_full_prefill(past(clone_alias=True), 3)

    def test_inconsistent_layer_lengths_rejected_before_copy(self):
        with self.assertRaisesRegex(PrefixCaptureError, "CONTEXT_LENGTH_MISMATCH"):
            capture_prefix_from_full_prefill((past()[0], past(6)[0]), 3)
        self.assertEqual(Tensor.allocations, 0)

    def test_one_full_forward_and_causal_prefix_equivalence(self):
        class CausalToy:
            def __init__(self):
                self.calls = 0
            def __call__(self, *, input_ids, use_cache):
                self.calls += 1
                assert use_cache
                running, keys, values = 0, [], []
                for token in input_ids:
                    running += token
                    keys.append(running)
                    values.append(2 * running)
                class Result:
                    past_key_values = ((Tensor(keys), Tensor(values)),)
                return Result()
        model = CausalToy()
        output, captured = prefill_and_capture(
            model, [2, 3, 5, 7], 2, expected_bytes=16)
        self.assertEqual(model.calls, 1)
        self.assertIsNotNone(output.past_key_values)
        self.assertEqual(captured[0][0].seq, [2, 5])
        self.assertEqual(captured[0][1].seq, [4, 10])
        oracle = CausalToy()(input_ids=[2, 3], use_cache=True)
        self.assertEqual(captured[0][0].seq, oracle.past_key_values[0][0].seq)
        self.assertEqual(captured[0][1].seq, oracle.past_key_values[0][1].seq)


if __name__ == "__main__":
    unittest.main()
