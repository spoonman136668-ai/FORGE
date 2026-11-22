"""Read-only receipt of actual persisted CKAD native checkpoints.

NOT training, cold restore, a trusted execution attestation, or permission.
"""
from __future__ import annotations
import json
from pathlib import Path
import re

from f139.ckad_campaign_request import CampaignDenied, need, seal_owner_result
from f139.ckad_stage_custody import MAX_RAW, canonical, digest

SCHEMA = "forge.ckad.persisted-native-stage-audit.v1"
NAME = re.compile(r"[a-z0-9][a-z0-9._-]{0,95}\Z")
BASE = frozenset({"schema", "source_mode", "properties_ascii", "source_ascii",
                  "hypotheses_ascii", "quarantined", "events",
                  "accepted_native", "scientific_pass"})
SCHEMA_FIELDS = {
    "yggdrasil.ckad.native-cumulative-learner.v1": BASE,
    "yggdrasil.ckad.native-cumulative-learner.v2": BASE | {"repairs"},
    "yggdrasil.ckad.native-cumulative-learner.v3": BASE | {"repairs", "history_ascii"},
    "yggdrasil.ckad.native-cumulative-learner.v4": BASE | {"repairs", "history_ascii", "dtr_ascii"},
    "yggdrasil.ckad.native-cumulative-learner.v5": BASE | {"repairs", "history_ascii", "dtr_ascii",
                                                          "experience_ascii", "experience_source"},
}


def _unique(pairs):
    result = {}
    for key, value in pairs:
        need(key not in result, "DUPLICATE_NATIVE_JSON_KEY")
        result[key] = value
    return result


def inspect_native_checkpoint(raw):
    """Only structural validation. Semantic validity needs CKAD cold restore."""
    need(type(raw) is bytes and 1 <= len(raw) <= MAX_RAW,
         "NATIVE_BYTES_MISSING_OR_OVERSIZE")
    try:
        obj = json.loads(raw.decode("ascii"), object_pairs_hook=_unique,
                         parse_constant=lambda _: need(False, "NONFINITE_NATIVE_JSON"))
    except (UnicodeError, ValueError, TypeError) as exc:
        raise CampaignDenied("FORGE_CKAD_CAMPAIGN_NATIVE_CHECKPOINT_JSON_INVALID") from exc
    need(type(obj) is dict and obj.get("schema") in SCHEMA_FIELDS,
         "NOT_NATIVE_CUMULATIVE_CHECKPOINT")
    need(set(obj) == SCHEMA_FIELDS[obj["schema"]]
         and obj["source_mode"] == "engineering_fixture_only"
         and obj["accepted_native"] is False and obj["scientific_pass"] is False
         and type(obj["properties_ascii"]) is str and bool(obj["properties_ascii"])
         and type(obj["source_ascii"]) is str and bool(obj["source_ascii"])
         and type(obj["hypotheses_ascii"]) is list and len(obj["hypotheses_ascii"]) == 16
         and all(h is None or type(h) is str for h in obj["hypotheses_ascii"])
         and type(obj["quarantined"]) is list and len(obj["quarantined"]) == 16
         and all(type(x) is bool for x in obj["quarantined"])
         and type(obj["events"]) is list and len(obj["events"]) <= 128
         and canonical(obj) == raw,
         "NATIVE_CHECKPOINT_STRUCTURE_DRIFT")
    return {"schema": obj["schema"], "sha256": digest(raw),
            "native_cold_restore_verified": False,
            "scientific_pass": False}


def _read(root, name):
    need(isinstance(root, Path) and type(name) is str
         and NAME.fullmatch(name) is not None
         and root.is_dir() and not root.is_symlink(),
         "ARTIFACT_ROOT_OR_BASENAME")
    base = root.resolve(strict=True)
    path = root / name
    need(path.is_file() and not path.is_symlink()
         and path.parent.resolve(strict=True) == base
         and path.resolve(strict=True).parent == base,
         "ARTIFACT_SYMLINK_OR_ESCAPE")
    before = path.stat()
    need(1 <= before.st_size <= MAX_RAW, "ARTIFACT_SIZE")
    raw = path.read_bytes()
    after = path.stat()
    need(len(raw) == before.st_size == after.st_size
         and before.st_mtime_ns == after.st_mtime_ns
         and before.st_ino == after.st_ino,
         "ARTIFACT_CHANGED_DURING_READ")
    return raw


def inspect_persisted_stage(campaign, receipts, stage_proposal, *, root,
                            independently_pinned_head=None, input_file,
                            output_file, evidence_file, control_file,
                            evaluation_file, observations, interventions,
                            cpu_seconds):
    """Seal five real disk files; no writes, training, or owner privileges."""
    names = (input_file, output_file, evidence_file, control_file, evaluation_file)
    need(len(set(names)) == 5, "ALIASED_ARTIFACTS")
    old, new, evidence, control, evaluation = (_read(root, n) for n in names)
    prior, after = inspect_native_checkpoint(old), inspect_native_checkpoint(new)
    receipt = seal_owner_result(
        campaign, receipts, stage_proposal,
        independently_pinned_head=independently_pinned_head,
        checkpoint_input=old, checkpoint_output=new,
        evidence_bytes=evidence, control_receipt_bytes=control,
        evaluation_receipt_bytes=evaluation,
        observations=observations, interventions=interventions,
        cpu_seconds=cpu_seconds,
    )
    need(receipt["input_checkpoint_sha256"] == prior["sha256"]
         and receipt["output_checkpoint_sha256"] == after["sha256"],
         "CHECKPOINT_AND_RECEIPT_MISMATCH")
    return {"schema": SCHEMA, "receipt": receipt, "files_read": 5,
            "input_native_schema": prior["schema"], "output_native_schema": after["schema"],
            "source_owner_run_authenticated": False,
            "native_cold_restore_verified": False,
            "stage_executed_by_forge": False,
            "training_execution_authorized": False,
            "scientific_pass": False, "promotion_authorized": False,
            "new_controller": False, "new_scheduler": False, "new_queue": False}
