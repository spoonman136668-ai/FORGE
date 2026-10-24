#!/usr/bin/env python3
"""Original TRAIN checkpoint equivalence on synthetic bytes, not WebNLG examples.

Preserves original L9 neural selectors, artifact archives, epochs and model source.
Does not load WebNLG or consume L9 SELECT/AUDIT_DEV/official TEST in this probe.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import time

import l9_model_suite as frozen
import l9_neural_select_only as selector
import l9_cached_encoder_parity as cache

ARTIFACTS = {
    1701: {
        "id": 12540689608,
        "zip_sha256": "17a90a22f1659a572f6987b73ff7e36bdf92d9f14b87a839f5d50a0cadc3adbc",
        "fit_receipt_sha256": "ab1ef4066a30a4f3d4be2b1b72b9c0ff48511cc353c4e5de5e1d5523199938c5",
        "checkpoints": {
            4: "5bc25aa6f0ff02690a8fec14a31b1d7ce5a6adf8a9355088327a2bcd22acd23e",
            8: "971919768cf8a62ef46df604d3b8754bf105db1afdf762dcae61b0d30e9602a3",
            12: "bf731132c64dbfd82ea5bc6121d0006c34527101b040119f9d11d83931a99a84",
        },
    },
    1702: {
        "id": 12540798385,
        "zip_sha256": "24bb0277b30fc90d69372ab25542379897a4c543a8b0010a2c9d8230972b733d",
        "fit_receipt_sha256": "39858e1c21d8b2e03463b2b244ba46693171564038b4787858ba052a27e51ed8",
        "checkpoints": {
            4: "31e39af09253a7ed6950ead93a834469a62ac6908dcfcc1cdeacde4e3d885238",
            8: "b414a71193c12cd54db71403af0c5edd50ac905372cf6d9920e5026e80f7bbb8",
            12: "e5e7baaf4a0ad3be69213933419da96fb85842a0b40adafdecd587d00fccf5a0",
        },
    }
}
EPOCHS = (4, 8, 12)
MAX_STEPS = 16
LOGIT_ABS_LIMIT = 2e-5
ROLE_SHA = "b9995c1846f5e1d99bf8bc4083dde0ebb41140906284bcf050a7ed6fe0efe726"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def require(condition, reason: str) -> None:
    if not condition:
        raise ValueError("L9_TRAINED_PARITY_REJECT:" + reason)


def synthetic_sources():
    """Invented in-code literals only, never external dataset rows."""
    cases = (
        (frozen.Triple("N0", "synthetic relation", "N1"),),
        (frozen.Triple("Node_A", "rel_1", "Node_B"),
         frozen.Triple("Node_B", "rel_2", "Node_C")),
        (frozen.Triple("long synthetic subject with spaces 01", "r1", "object 02"),
         frozen.Triple("subject 03", "long synthetic relation 04", "object 05"),
         frozen.Triple("subject 06", "rel_3", "long synthetic object 07")),
    )
    for triples in cases:
        ids = frozen.encode_source(triples)
        require(ids is not None and len(ids) > 1 and ids[-1] == frozen.EOS and
                all(0 <= i < 256 for i in ids[:-1]),
                "INVALID_SYNTHETIC_SOURCE")
        yield ids


def checkpoint_custody(folder: Path, seed: int) -> dict:
    require(seed in ARTIFACTS, "UNAPPROVED_SEED")
    expected = ARTIFACTS[seed]
    raw = (folder / "receipt.json").read_bytes()
    require(digest(raw) == expected["fit_receipt_sha256"],
            "ORIGINAL_TRAIN_FIT_RECEIPT_HASH_DRIFT")
    original = json.loads(raw)
    selector.assert_fit_receipt(original, "SMALL_TRANSFORMER", seed)
    for epoch in EPOCHS:
        info = original["checkpoints"][str(epoch)]
        require(info["inference_sha256"] == expected["checkpoints"][epoch],
                "FROZEN_CHECKPOINT_ID_DRIFT")
        name = f"SMALL_TRANSFORMER-seed{seed}-epoch{epoch}-inference.pt"
        require(info["inference_file"] == name, "CHECKPOINT_FILENAME_DRIFT")
        ckpt = (folder / name).read_bytes()
        require(digest(ckpt) == expected["checkpoints"][epoch],
                "CHECKPOINT_BYTES_DRIFT")
        require(len(ckpt) == info["inference_bytes"] == 1721741,
                "CHECKPOINT_BYTE_LENGTH_DRIFT")
    require(sorted(f.name for f in folder.iterdir()) ==
            sorted(["receipt.json"] +
                   [f"SMALL_TRANSFORMER-seed{seed}-epoch{e}-inference.pt"
                    for e in EPOCHS]), "UNEXPECTED_TRAIN_ARTIFACT_MEMBER")
    return expected


def compare_one(net, ids: list[int]) -> dict:
    import torch
    src = torch.tensor([ids], dtype=torch.long)
    enc_calls = [0]
    def register(_module, _inputs, _output):
        enc_calls[0] += 1
    handle = net.transformer.encoder.register_forward_hook(register)
    try:
        with torch.inference_mode():
            begin = time.perf_counter()
            original = net.greedy(src, max_steps=MAX_STEPS)
            original_s = time.perf_counter() - begin
            full_calls = enc_calls[0]
            enc_calls[0] = 0
            begin = time.perf_counter()
            cached = cache.cached_encoder_greedy(net, src, max_steps=MAX_STEPS)
            cached_s = time.perf_counter() - begin
            cached_calls = enc_calls[0]

            # Do NOT treat a one-time microbenchmark as real SELECT efficiency.
            require(torch.equal(original, cached),
                    "ORIGINAL_TRAINED_GREEDY_TOKEN_DIVERGENCE")
            require(full_calls == original.shape[1], "FULL_FORWARD_COUNT_DRIFT")
            require(cached_calls == 1, "CACHED_FORWARD_COUNT_DRIFT")
            prefix = torch.cat((
                torch.tensor([[frozen.BOS]], dtype=torch.long),
                original[:, :min(5, original.shape[1])]), dim=1)
            actual = net.forward(src, prefix)[:, -1, :]
            memory = net.transformer.encoder(
                net._embed(src), src_key_padding_mask=(src == frozen.PAD))
            causal = torch.nn.Transformer.generate_square_subsequent_mask(
                prefix.shape[1], device=prefix.device)
            output = net.transformer.decoder(
                net._embed(prefix), memory, tgt_mask=causal,
                tgt_key_padding_mask=(prefix == frozen.PAD),
                memory_key_padding_mask=(src == frozen.PAD))
            equivalent = net.output(output)[:, -1, :]
            max_abs_error = (actual-equivalent).abs().max().item()
            require(math.isfinite(max_abs_error) and
                    max_abs_error <= LOGIT_ABS_LIMIT, "TRAINED_LOGIT_DIVERGENCE")
            return {
                "synthetic_input_bytes": len(ids),
                "generated_tokens": original.shape[1],
                "token_ids_sha256": digest(json.dumps(
                    original[0].tolist(), separators=(",", ":")).encode("utf8")),
                "exact_tokens": True,
                "original_encoder_calls": full_calls,
                "cached_encoder_calls": cached_calls,
                "maximum_abs_logit_error": round(max_abs_error, 12),
                "original_wall_s": round(original_s, 6),
                "cached_wall_s": round(cached_s, 6),
                "timings_not_qualified_for_pareto": True,
            }
    finally:
        handle.remove()


def run(folder: Path, seed: int) -> dict:
    import torch
    cache.require_frozen_source(Path(__file__).resolve().parent)
    require(seed in ARTIFACTS, "UNQUALIFIED_SEED")
    checkpoint_custody(folder, seed)
    require(torch.__version__.split("+")[0] == "2.5.1" and
            not torch.cuda.is_available(), "UNQUALIFIED_TORCH_RUNTIME")
    torch.set_num_threads(2)
    rows = []
    synthetic = list(synthetic_sources())
    for epoch in EPOCHS:
        net, info = selector.model_from_checkpoint("SMALL_TRANSFORMER",
                                                   seed, epoch, folder)
        require(not net.training, "CHECKPOINT_NOT_EVAL")
        epoch_rows = [compare_one(net, ids) for ids in synthetic]
        rows.append({
            "epoch": epoch,
            "checkpoint_sha256": info["inference_sha256"],
            "source_test_count": len(epoch_rows),
            "synthetic_results": epoch_rows,
        })
        del net

    return {
        "schema": "forge.optimizer.language.l9.trained-encoder-synthetic-parity-v1",
        "classification": "FROZEN_TRAIN_CHECKPOINT_SYNTHETIC_ENGINEERING_ONLY",
        "model_suite_git_blob": cache.FROZEN_MODEL_BLOB,
        "select_evaluator_git_blob": cache.FROZEN_SELECT_BLOB,
        "train_role_identity_sha256": ROLE_SHA,
        "seed": seed,
        "verified_original_artifact_id": ARTIFACTS[seed]["id"],
        "verified_original_artifact_zip_sha256": ARTIFACTS[seed]["zip_sha256"],
        "verified_original_fit_receipt_sha256":
            ARTIFACTS[seed]["fit_receipt_sha256"],
        "all_frozen_epochs": list(EPOCHS),
        "synthetic_sources_per_checkpoint": len(synthetic),
        "original_train_weights_loaded": True,
        "fit_reperformed": False,
        "original_select_scored": False,
        "audit_dev_scored": False,
        "official_test_scored": False,
        "trained_checkpoint_token_parity": True,
        "original_model_or_evaluator_modified": False,
        "hardware_matched_comparison": False,
        "resource_pareto_qualified": False,
        "scientific_go": False,
        "torch_version": torch.__version__,
        "results": rows,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--artifact-dir", type=Path, required=True)
    p.add_argument("--seed", type=int, choices=sorted(ARTIFACTS), required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    require(not a.out.exists(), "RECEIPT_OVERWRITE")
    report = run(a.artifact_dir, a.seed)
    a.out.write_bytes((json.dumps(report, sort_keys=True,
                       separators=(",", ":")) + "\n").encode("utf8"))
    print("L9_REAL_FROZEN_TRAIN_CHECKPOINTS_SYNTHETIC_PARITY=PASS")
    print("L9_TRAINED_WEIGHTS_SOURCE_SHA256_VERIFIED=TRUE")
    print("L9_L9_SELECT_OR_AUDIT_USED=FALSE")
    print("L9_SCIENTIFIC_COST_PARETO_QUALIFIED=FALSE")


if __name__ == "__main__":
    main()
