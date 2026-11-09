"""Read immutable, owner-merged ITD-02 guidance at F139's existing idle intake.

This source-only advisor cannot issue work, mutate the ledger, authorize first
use or change an already-admitted task. Unavailable guidance preserves legacy
candidate order with an explicit status; malformed pinned bytes are rejected.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
from typing import Callable

MERGED_STEERING_COMMIT = "2a3c9453ba36c983b7b1dee0bb6ab1371108141b"
REPOSITORY = "spoonman136668-ai/FORGE"
# Exact original Git blob identities from operator-merged PR #979.
DOCUMENTS = (
    ("docs/FORGE-INFO-PER-COMPUTE-NORTH-STAR.md",
     "51d26d3b9b821b06fd78c87af3156f5989b0329e"),
    ("docs/research-steering/CORE-NATIVE-INTELLIGENCE.md",
     "d867957f4e3311554744bf1036f9af63d86a2df0"),
    ("docs/research-steering/LEARNING-MECHANISM-DISCOVERY.md",
     "22d62f0856594554f7cc32d0cdeb2326bf9264d7"),
    ("docs/research-steering/INDEPENDENT-SCIENTIFIC-VALIDATION.md",
     "e4b03f73193115a846a39be2ec2c8530143386ec"),
)
MAX_BYTES = 16384
LANES = ("Wingless", "Yggdrasil", "TTT-Hybrid")


class SteeringDenied(ValueError):
    pass


def require(ok: bool, reason: str) -> None:
    if not ok:
        raise SteeringDenied("F139_RESEARCH_STEERING_" + reason)


def _read_one(get: Callable[[str], object], path: str, sha: str) -> str:
    route = ("repos/" + REPOSITORY + "/contents/" + path
             + "?ref=" + MERGED_STEERING_COMMIT)
    doc = get(route)
    require(isinstance(doc, dict) and doc.get("type") == "file"
            and doc.get("encoding") == "base64"
            and doc.get("sha") == sha
            and type(doc.get("size")) is int
            and 0 < doc["size"] <= MAX_BYTES
            and isinstance(doc.get("content"), str),
            "DOCUMENT_METADATA_INVALID")
    encoded = doc["content"].replace("\n", "")
    try:
        raw = base64.b64decode(encoded, validate=True)
        text = raw.decode("utf-8", errors="strict")
    except (UnicodeError, ValueError, binascii.Error) as exc:
        raise SteeringDenied("F139_RESEARCH_STEERING_DOCUMENT_BYTES_INVALID") from exc
    git_blob = hashlib.sha1(
        b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw
    ).hexdigest()
    require(git_blob == sha and len(raw) == doc["size"]
            and base64.b64encode(raw).decode("ascii") == encoded
            and "\x00" not in text, "DOCUMENT_IDENTITY_DRIFT")
    return text


def read_approved_steering(get: Callable[[str], object]) -> dict:
    """Authenticate four bounded exact Git blobs; return only advisory metadata."""
    require(callable(get), "PROVIDER_INVALID")
    texts = {path: _read_one(get, path, sha) for path, sha in DOCUMENTS}
    root, core, discovery, validation = (
        texts[DOCUMENTS[i][0]] for i in range(4))
    require(all(path.split("/")[-1] in root for path, _ in DOCUMENTS[1:])
            and "advisory" in root.lower()
            and "decision-discriminating" in core.lower()
            and "integration" in core.lower()
            and "learning-progress" in discovery.lower()
            and "multi-fidelity" in discovery.lower()
            and "independent" in validation.lower()
            and "ablation" in validation.lower(),
            "DOCUMENT_SCOPE_INVALID")
    manifest = ("\n".join(path + ":" + sha for path, sha in DOCUMENTS)
                + "\n").encode("ascii")
    return {
        "schema": "forge.f139.itd02-steering-consumption.v1",
        "status": "VERIFIED_ADVISORY_ONLY",
        "source_commit": MERGED_STEERING_COMMIT,
        "manifest_sha256": hashlib.sha256(manifest).hexdigest(),
        "documents": len(DOCUMENTS),
        "next_eligible_development_only": True,
        "scientific_first_use": False,
        "dispatch_authorized": False,
        "accepted_ref_mutation": False,
    }


def fair_lane_order(admitted_lanes: tuple[str, ...] = ()) -> tuple[str, ...]:
    """Least recently admitted first, reconstructed from verified owner events.

    No clock, persisted cursor, queue or provider completion inference. Only
    genuine owner admissions advance service; failed/unavailable lanes cannot
    reserve capacity. Unserved lanes tie in the existing fixed policy order.
    """
    require(isinstance(admitted_lanes, tuple)
            and all(isinstance(lane, str) and lane in LANES
                    for lane in admitted_lanes), "ADMISSION_HISTORY_INVALID")
    last = {lane: -1 for lane in LANES}
    for index, lane in enumerate(admitted_lanes):
        last[lane] = index
    return tuple(sorted(LANES, key=lambda lane: last[lane]))


def rank_eligible(candidates: list[dict], *, maximum: int = 2,
                  admitted_lanes: tuple[str, ...] = (),
                  use_forecasts: bool = True) -> list[dict]:
    """Prefer authenticated advisory information/compute estimates, with lane fairness.

    Inputs are *already* original-owner PR/Git-verified development candidates.
    Forecasts are estimates, never science; no candidate is made eligible here.
    Preserve catalog order for equal or absent scores within each lane. Serve
    least recently admitted lanes first, one place each before surplus places.
    The caller supplies only already-verified original-owner admission history.
    """
    require(type(maximum) is int and maximum == 2
            and type(use_forecasts) is bool
            and isinstance(candidates, list)
            and all(isinstance(c, dict) and c.get("lane") in LANES
                    for c in candidates), "RANK_INPUT_INVALID")
    lane_order = fair_lane_order(admitted_lanes)
    def score(c: dict) -> tuple[int, int]:
        a = c.get("advisory_handoff")
        if not use_forecasts or not isinstance(a, dict) or a.get("advisory_only") is not True:
            return (0, 0)
        information = a.get("expected_information_microbits")
        cost = a.get("estimated_compute_units")
        if type(information) is not int or type(cost) is not int or cost <= 0:
            return (0, 0)
        # Advisory integers cannot turn into unbounded scores.
        return (1, min(information, 10**12) * 1000 // max(1, min(cost, 10**12)))

    result, selected = [], set()
    for lane in lane_order:
        choices = [(i, c) for i, c in enumerate(candidates)
                   if c["lane"] == lane]
        if not choices:
            continue
        if len(result) == maximum:
            break
        i, candidate = max(choices, key=lambda x: (score(x[1]), -x[0]))
        result.append(candidate)
        selected.add(i)
    rest = [(i, c) for i, c in enumerate(candidates) if i not in selected]
    rest.sort(key=lambda x: (score(x[1]), -x[0]), reverse=True)
    result.extend(c for _, c in rest[:maximum - len(result)])
    return result[:maximum]
