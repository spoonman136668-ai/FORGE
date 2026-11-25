"""Pinned Dataset Registry & Split-Leakage Guard for FORGE F139 (Gate 21).

Lets researchers register ANY local text, byte, or JSONL dataset into FORGE
with cryptographic SHA-256 split pinning and fail-closed zero-overlap leakage
checks across `train`, `dev`, and `heldout_ood` splits.

Zero network calls, zero paid model calls, strictly read-only on source files.
"""
from __future__ import annotations

from pathlib import Path

from f139.nci04_native_contract import canonical, digest

DATASET_SCHEMA = "forge.f139.pinned-dataset-manifest.v1"


class DatasetRegistryDenied(ValueError):
    """Fail-closed denial for missing splits, symlinks, or train/eval leakage."""


def need(ok: bool, reason: str) -> None:
    if not ok:
        raise DatasetRegistryDenied("F139_DATASET_" + reason)


def _read_split_samples(path: Path) -> tuple[bytes, set[str], int]:
    p = Path(path)
    need(p.is_file() and not p.is_symlink(), "SPLIT_FILE_MISSING_OR_SYMLINK")
    raw = p.read_bytes()
    need(len(raw) > 0, "SPLIT_FILE_EMPTY")
    lines = [ln.strip() for ln in raw.decode("utf-8", errors="replace").splitlines() if ln.strip()]
    need(len(lines) > 0, "SPLIT_NO_NONEMPTY_SAMPLES")
    hashes = {digest(ln.encode("utf-8")) for ln in lines}
    return raw, hashes, len(lines)


def register_pinned_dataset(
    *,
    dataset_id: str,
    train_path: Path,
    dev_path: Path,
    heldout_ood_path: Path | None = None,
    description: str = "",
) -> dict:
    """Pin local dataset splits by SHA-256 and fail closed on any cross-split leakage."""
    need(type(dataset_id) is str and 2 <= len(dataset_id) <= 128, "DATASET_ID_INVALID")

    train_raw, train_hashes, train_n = _read_split_samples(train_path)
    dev_raw, dev_hashes, dev_n = _read_split_samples(dev_path)
    need(train_hashes.isdisjoint(dev_hashes), "TRAIN_DEV_LEAKAGE_DETECTED")

    splits = {
        "train": {
            "path": str(Path(train_path).resolve()),
            "sha256": digest(train_raw),
            "bytes": len(train_raw),
            "samples": train_n,
        },
        "dev": {
            "path": str(Path(dev_path).resolve()),
            "sha256": digest(dev_raw),
            "bytes": len(dev_raw),
            "samples": dev_n,
        },
    }

    if heldout_ood_path is not None:
        ho_raw, ho_hashes, ho_n = _read_split_samples(heldout_ood_path)
        need(train_hashes.isdisjoint(ho_hashes), "TRAIN_HELDOUT_LEAKAGE_DETECTED")
        need(dev_hashes.isdisjoint(ho_hashes), "DEV_HELDOUT_LEAKAGE_DETECTED")
        splits["heldout_ood"] = {
            "path": str(Path(heldout_ood_path).resolve()),
            "sha256": digest(ho_raw),
            "bytes": len(ho_raw),
            "samples": ho_n,
        }

    manifest = {
        "schema": DATASET_SCHEMA,
        "dataset_id": dataset_id,
        "description": str(description)[:256],
        "zero_split_leakage_verified": True,
        "splits": splits,
        "paid_model_calls": 0,
    }
    manifest["manifest_sha256"] = digest(canonical(manifest))
    return manifest
