"""Content-Addressed Write-Once Checkpoint Vault for FORGE F139 (Gate 20).

Preserves verified experiment/training checkpoints beyond ephemeral temporary
workspaces so FORGE can reload exact model states for independent held-out OOD
evaluation, ablations, or warm-start follow-up runs.

Hard boundaries:
- Strictly content-addressed by SHA-256 (`blobs/<sha256>.bin` + `meta/<sha256>.json`).
- Write-once / immutable: re-storing identical bytes deduplicates safely; any
  on-disk corruption is detected fail-closed on reload.
- Enforces hard disk quota (`max_vault_bytes`) and forbids `.sqlite` or symlinks.
- Never auto-promotes checkpoints (`auto_promote_checkpoint: False`,
  `scientific_first_use: False`, `paid_model_calls: 0`).
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import time

from f139.nci04_native_contract import canonical, digest

VAULT_META_SCHEMA = "forge.f139.checkpoint-vault-entry.v1"
DEFAULT_MAX_VAULT_BYTES = 512 * 1024 * 1024  # 512 MB


class CheckpointVaultDenied(ValueError):
    """Fail-closed denial for vault quota, path, or integrity violations."""


def need(ok: bool, reason: str) -> None:
    if not ok:
        raise CheckpointVaultDenied("F139_CKPT_VAULT_" + reason)


def _validate_vault_root(vault_root: Path) -> Path:
    root = Path(vault_root)
    need(not root.is_symlink(), "VAULT_SYMLINK_FORBIDDEN")
    need(root.suffix.lower() not in (".sqlite", ".sqlite3", ".db"), "SQLITE_PATH_FORBIDDEN")
    return root


def vault_disk_usage_bytes(vault_root: Path) -> int:
    """Return total bytes currently occupied by stored checkpoint blobs."""
    root = _validate_vault_root(vault_root)
    blobs = root / "blobs"
    if not blobs.is_dir():
        return 0
    return sum(f.stat().st_size for f in blobs.iterdir() if f.is_file() and not f.is_symlink())


def store_checkpoint(
    vault_root: Path,
    *,
    checkpoint_bytes: bytes,
    experiment_id: str,
    method_family: str,
    metric_summary: dict | None = None,
    max_vault_bytes: int = DEFAULT_MAX_VAULT_BYTES,
) -> dict:
    """Store a verified checkpoint in the content-addressed vault (write-once)."""
    root = _validate_vault_root(vault_root)
    need(type(checkpoint_bytes) is bytes and 0 < len(checkpoint_bytes) <= max_vault_bytes,
         "CHECKPOINT_BYTES_INVALID")
    need(type(experiment_id) is str and 2 <= len(experiment_id) <= 128, "EXPERIMENT_ID_INVALID")
    need(type(method_family) is str and 2 <= len(method_family) <= 64, "METHOD_FAMILY_INVALID")
    need(type(max_vault_bytes) is int and max_vault_bytes >= 1024, "QUOTA_INVALID")

    ckpt_sha = digest(checkpoint_bytes)
    blobs_dir = root / "blobs"
    meta_dir = root / "meta"
    blobs_dir.mkdir(parents=True, exist_ok=True)
    meta_dir.mkdir(parents=True, exist_ok=True)

    blob_path = blobs_dir / f"{ckpt_sha}.bin"
    meta_path = meta_dir / f"{ckpt_sha}.json"

    if blob_path.exists():
        # Deduplicate safely after verifying existing bytes match exact SHA-256
        need(not blob_path.is_symlink() and digest(blob_path.read_bytes()) == ckpt_sha,
             "EXISTING_BLOB_CORRUPTED")
        if meta_path.is_file():
            return json.loads(meta_path.read_text(encoding="utf-8"))
    else:
        current_usage = vault_disk_usage_bytes(root)
        need(current_usage + len(checkpoint_bytes) <= max_vault_bytes, "VAULT_QUOTA_EXCEEDED")
        with blob_path.open("xb") as f:
            f.write(checkpoint_bytes)
            f.flush()
            os.fsync(f.fileno())

    unsigned = {
        "schema": VAULT_META_SCHEMA,
        "checkpoint_sha256": ckpt_sha,
        "size_bytes": len(checkpoint_bytes),
        "experiment_id": experiment_id,
        "method_family": method_family,
        "metric_summary": dict(metric_summary or {}),
        "stored_at_unix": int(time.time()),
        "paid_model_calls": 0,
        "auto_promote_checkpoint": False,
        "scientific_first_use": False,
    }
    entry = dict(unsigned, entry_sha256=digest(canonical(unsigned)))
    if not meta_path.exists():
        with meta_path.open("xb") as f:
            f.write(canonical(entry))
            f.flush()
            os.fsync(f.fileno())
    return entry


def load_checkpoint(vault_root: Path, checkpoint_sha256: str) -> tuple[bytes, dict]:
    """Load and cryptographically verify a checkpoint and its metadata from the vault."""
    root = _validate_vault_root(vault_root)
    need(type(checkpoint_sha256) is str and len(checkpoint_sha256) == 64
         and all(c in "0123456789abcdef" for c in checkpoint_sha256),
         "CHECKPOINT_SHA_INVALID")
    blob_path = root / "blobs" / f"{checkpoint_sha256}.bin"
    meta_path = root / "meta" / f"{checkpoint_sha256}.json"
    need(blob_path.is_file() and not blob_path.is_symlink(), "CHECKPOINT_BLOB_MISSING")
    need(meta_path.is_file() and not meta_path.is_symlink(), "CHECKPOINT_META_MISSING")

    raw_blob = blob_path.read_bytes()
    need(digest(raw_blob) == checkpoint_sha256, "CHECKPOINT_BLOB_TAMPERED")

    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    sig = meta.get("entry_sha256")
    unsigned = {k: v for k, v in meta.items() if k != "entry_sha256"}
    need(digest(canonical(unsigned)) == sig and meta.get("checkpoint_sha256") == checkpoint_sha256,
         "CHECKPOINT_META_TAMPERED")
    return raw_blob, meta


def list_vault_checkpoints(vault_root: Path) -> list[dict]:
    """List metadata entries for all verified checkpoints in the vault."""
    root = _validate_vault_root(vault_root)
    meta_dir = root / "meta"
    if not meta_dir.is_dir():
        return []
    entries = []
    for f in sorted(meta_dir.glob("*.json")):
        if f.is_file() and not f.is_symlink():
            entries.append(json.loads(f.read_text(encoding="utf-8")))
    return entries
