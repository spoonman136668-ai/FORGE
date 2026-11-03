"""G101 isolated adapter verification with no original checkpoint or dataset."""
import hashlib
import json
import types
import unittest
from contextlib import nullcontext
from unittest.mock import patch

from research.cpu_g97 import g101_original_adapter as candidate
from research.cpu_g97.test_g101_prefix_capture import Tensor


class Ids:
    def __init__(self, values):
        self.values = list(values)
        self.shape = (1, len(self.values))


class FakeTorch:
    @staticmethod
    def inference_mode():
        return nullcontext()
    @staticmethod
    def cat(parts, dim):
        assert dim == 1
        return Ids(parts[0].values + parts[1].values)


class FakeProcess:
    def memory_info(self):
        return types.SimpleNamespace(rss=40000)


class FakeModel:
    def __init__(self, bad=False):
        self.full_calls = 0
        self.cached_calls = 0
        self.bad = bad
    def __call__(self, *, input_ids, use_cache, past_key_values=None):
        if not use_cache:
            raise AssertionError("uncached forward")
        if past_key_values is None:
            self.full_calls += 1
            n = len(input_ids.values) + (1 if self.bad else 0)
            past = ((Tensor(list(range(n))), Tensor([20 + i for i in range(n)])),)
        else:
            self.cached_calls += 1
            past = past_key_values
        return types.SimpleNamespace(past_key_values=past)


class FakeG95:
    TOKENS = 2
    @staticmethod
    def baseline_request(model, full, tokens, torch, proc):
        out = model(input_ids=full, use_cache=True)
        assert out.past_key_values
        return [sum(full.values), tokens], {"rss_bytes": proc.memory_info().rss}
    @staticmethod
    def request_decode(model, full, suffix, past, prefix_length, tokens, torch, proc):
        assert len(past[0][0].seq) == prefix_length
        model(input_ids=suffix, past_key_values=past, use_cache=True)
        return [sum(full.values), tokens], {"rss_bytes": proc.memory_info().rss}
    @staticmethod
    def tensor_tree_bytes(tree):
        return sum(t.numel() * t.element_size() for layer in tree for t in layer)
    @staticmethod
    def tensor_tree_digest(tree):
        return hashlib.sha256(json.dumps(
            [[t.seq for t in layer] for layer in tree]).encode()).hexdigest()
    @staticmethod
    def tensor_storage_ptrs(tree):
        return {t.data_ptr() for layer in tree for t in layer}


def inputs():
    prefixes = [Ids([2, 3]), Ids([4, 5])]
    keys = ["key-a", "key-b"]
    requests = [{"prefix_id": pid, "suffix": Ids([6 + i]),
                 "source_row": i, "prefix_kv_bytes": 16}
                for i, pid in enumerate((0, 1, 0, 1))]
    return requests, prefixes, keys


class G101AdapterTests(unittest.TestCase):
    def invoke(self, model=None, stream=None):
        model = model or FakeModel()
        original_stream, prefixes, keys = inputs()
        stream = original_stream if stream is None else stream
        with patch.object(candidate.g97.frozen, "_g95", return_value=FakeG95):
            return model, candidate.run_g101(
                model, stream, prefixes, keys, FakeTorch, FakeProcess())

    def test_full_prefill_once_per_miss_and_exact_outputs(self):
        model, (outputs, metrics) = self.invoke()
        self.assertEqual(model.full_calls, 2)
        self.assertEqual(model.cached_calls, 2)
        self.assertEqual(metrics["extra_prefix_forwards"], 0)
        self.assertEqual(metrics["capture_events"], 2)
        self.assertEqual((metrics["hits"], metrics["misses"],
                          metrics["admissions"], metrics["evictions"]), (2, 2, 2, 0))
        self.assertEqual([r["served_from_cache"] for r in metrics["rows"]],
                         [False, False, True, True])
        self.assertEqual([r["used_full_prefill"] for r in metrics["rows"]],
                         [True, True, False, False])
        for idx, req in enumerate(inputs()[0]):
            full = inputs()[1][req["prefix_id"]].values + req["suffix"].values
            self.assertEqual(outputs[idx], [sum(full), FakeG95.TOKENS])
            self.assertEqual(metrics["rows"][idx]["output_sha256"],
                             hashlib.sha256(json.dumps(
                                 outputs[idx], separators=(",", ":")).encode()).hexdigest())
        self.assertEqual(metrics["max_resident_kv_bytes"], 32)

    def test_mismatch_rejected_before_storage_admission(self):
        model = FakeModel(bad=True)
        with self.assertRaisesRegex(ValueError, "CONTEXT_LENGTH_MISMATCH|EXPECTED_BYTES_DRIFT"):
            self.invoke(model=model)
        self.assertEqual(model.full_calls, 1)
        self.assertEqual(model.cached_calls, 0)

    def test_bad_expected_bytes_fail_before_inference(self):
        req, _, _ = inputs()
        req[0]["prefix_kv_bytes"] = candidate.BYTE_LIMIT + 1
        model = FakeModel()
        with self.assertRaisesRegex(RuntimeError, "BUDGET_OR_SIZE_INVALID"):
            self.invoke(model=model, stream=req)
        self.assertEqual(model.full_calls, 0)

    def test_distinct_requests_cannot_alias_prefixes(self):
        model = FakeModel()
        with self.assertRaisesRegex(ValueError, "INVALID_STREAM_OR_KEYS"):
            candidate.run_g101(model, inputs()[0], inputs()[1],
                               ["same-key", "same-key"], FakeTorch, FakeProcess())
        self.assertEqual(model.full_calls, 0)

    def test_failure_does_not_monkeypatch_frozen_controller(self):
        original = candidate.g97.frozen.AdmissionCache
        with self.assertRaisesRegex(ValueError, "EXPECTED_BYTES_DRIFT|CONTEXT_LENGTH_MISMATCH"):
            self.invoke(model=FakeModel(bad=True))
        self.assertIs(candidate.g97.frozen.AdmissionCache, original)


if __name__ == "__main__":
    unittest.main()
