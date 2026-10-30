"""Offline-source tests only; no model import, download or GPU required."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("g60", Path(__file__).with_name("g60_gpu_baseline.py"))
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)

class G60SourceTests(unittest.TestCase):
    def test_checkpoint_and_revision_not_mutated(self):
        self.assertEqual(g.REV, "607a30d783dfa663caf39e06633721c8d4cfcd7e")
        self.assertEqual(g.WEIGHT_SHA, "248dfc3911869ec493c76e65bf2fcf7f615828b0254c12b473182f0f81d3a707")
    def test_fixed_repeats_contexts(self):
        self.assertEqual(g.CONTEXTS, (128, 384))
        self.assertEqual(g.GENERATED, 32)
        self.assertEqual(g.REPS, 5)
    def test_source_digest(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)/"sample"
            p.write_bytes(b"abc")
            self.assertEqual(g.sha256(p),
                             "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad")
    def test_paired_medians(self):
        x=[{"prefill_s":s,"decode_32_s":2*s,"full_inference_s":3*s} for s in (1,3,2,5,4)]
        self.assertEqual(g.pack(x), {"prefill_s":3,"decode_32_s":6,"full_inference_s":9})
    def test_artifact_output_contract(self):
        self.assertEqual(g.REPO,"openai-community/gpt2")
        self.assertEqual(len(g.FILES),7)
        self.assertIn("model.safetensors",g.FILES)
    def test_no_candidate_speedup_assertion(self):
        s=Path(__file__).with_name("g60_gpu_baseline.py").read_text()
        self.assertIn('"novel_acceleration_established": False',s)
        self.assertIn('"production_optimized_baseline": False',s)
        self.assertIn("MODEL_CPU_FALLBACK",s)
        self.assertIn("CPU_CUDA_GREEDY_OUTPUT_MISMATCH",s)

if __name__=="__main__":
    unittest.main()
