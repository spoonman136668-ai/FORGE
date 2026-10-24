"""Fail-closed frozen original TRAIN checkpoint identity and synthetic-only inputs."""
import copy
import json
import hashlib
import tempfile
from pathlib import Path
import unittest
import l9_trained_encoder_parity as p


class TrainedParityTests(unittest.TestCase):
    def test_two_seeds_three_epochs_all_original_hashes(self):
        self.assertEqual(set(p.ARTIFACTS), {1701, 1702})
        self.assertEqual(p.EPOCHS, (4, 8, 12))
        self.assertEqual(p.MAX_STEPS, 16)
        self.assertEqual(p.ROLE_SHA,
                         "b9995c1846f5e1d99bf8bc4083dde0ebb41140906284bcf050a7ed6fe0efe726")
        for seed, row in p.ARTIFACTS.items():
            self.assertEqual(set(row["checkpoints"]), {4, 8, 12})
            self.assertEqual(len(row["checkpoints"]), 3)
            for value in [row["zip_sha256"],
                          row["fit_receipt_sha256"], *row["checkpoints"].values()]:
                self.assertEqual(len(value), 64)
                self.assertTrue(all(c in "0123456789abcdef" for c in value))

    def test_original_frozen_model_and_selector_exact_blobs(self):
        root = Path(__file__).resolve().parent
        p.cache.require_frozen_source(root)
        self.assertEqual(p.selector.SUITE_BLOB, p.cache.FROZEN_MODEL_BLOB)

    def test_synthetic_inputs_have_no_external_data(self):
        sources = list(p.synthetic_sources())
        self.assertEqual(len(sources), 3)
        self.assertTrue(all(1 < len(x) <= 2049 and x[-1] == p.frozen.EOS and
                            all(0 <= v <= 255 for v in x[:-1]) for x in sources))
        self.assertEqual(len({hashlib.sha256(json.dumps(x).encode()).hexdigest()
                              for x in sources}), 3)

    def test_reject_missing_artifact_before_model_execution(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(FileNotFoundError):
                p.checkpoint_custody(Path(d), 1701)

    def test_unknown_artifact_seed_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError, "UNAPPROVED_SEED"):
                p.checkpoint_custody(Path(d), 1703)

    def test_original_receipt_byte_tamper_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "receipt.json").write_text("{}")
            with self.assertRaisesRegex(ValueError, "FIT_RECEIPT_HASH_DRIFT"):
                p.checkpoint_custody(root, 1701)

    def test_never_parses_corpus_or_scores_original_roles(self):
        raw = (Path(__file__).resolve().parent /
               "l9_trained_encoder_parity.py").read_text()
        for forbidden in ("load_train_select(", "load_audit(",
                          "webnlg-dataset", "git clone", "subprocess.run(",
                          "train_neural(", "compute_select_metric("):
            self.assertNotIn(forbidden, raw)


if __name__ == "__main__":
    unittest.main()
