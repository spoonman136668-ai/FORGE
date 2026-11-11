"""R13: inert FORGE-self source hazard and train-only repair-memory selection.

One source-authenticated Go repair template. No Git writes, arbitrary code
execution, external provider, original-owner admission, or RSI success claim.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha1, sha256
import re

SCHEMA = "forge.f139.rsi-r13.source-falsifier.dev.v1"
TARGET = "cmd/forge-lane-watchdog/main.go"
ORIGINAL_BLOB = "0c30f74434c6defcb7606a697596c7f59946c730"
MAX_SOURCE = 100_000
SHA64 = re.compile(r"[0-9a-f]{64}\Z")
ALLOWED_MECHANISMS = frozenset({"strict-sentinel", "reject-on-size-drift", "no-change"})
ANCHOR_IMPORT = 'import(\n "crypto/ed25519"\n'
ANCHOR_READER = (
    ' dec:=json.NewDecoder(io.LimitReader(f,65537));dec.DisallowUnknownFields()\n'
    ' if err:=dec.Decode(target);err!=nil{return err}\n'
    ' var extra any\n'
    ' if !errors.Is(dec.Decode(&extra),io.EOF){return fmt.Errorf("trailing witness input rejected")}\n'
    ' return nil\n'
    '}\n'
    'func run('
)
REPLACEMENT_READER = (
    ' return decodeBoundedWitness(f,target)\n'
    '}\n'
    '// A reader-size sentinel is checked BEFORE parsing or mutating the target.\n'
    'func decodeBoundedWitness(in io.Reader,target any)error{\n'
    ' raw,err:=io.ReadAll(io.LimitReader(in,65537))\n'
    ' if err!=nil||len(raw)==0||len(raw)>65536{\n'
    '  return errors.New("witness input read failed or changed size")\n'
    ' }\n'
    ' dec:=json.NewDecoder(bytes.NewReader(raw));dec.DisallowUnknownFields()\n'
    ' if err:=dec.Decode(target);err!=nil{return err}\n'
    ' var extra any\n'
    ' if !errors.Is(dec.Decode(&extra),io.EOF){return fmt.Errorf("trailing witness input rejected")}\n'
    ' return nil\n'
    '}\n'
    'func run('
)


class FalsifierDenied(ValueError):
    pass


def need(ok: bool, why: str) -> None:
    if not ok:
        raise FalsifierDenied("FORGE_RSI_R13_" + why)


def git_blob(raw: bytes) -> str:
    need(type(raw) is bytes, "SOURCE_BYTES_REQUIRED")
    return sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def digest(raw: bytes) -> str:
    return sha256(raw).hexdigest()


@dataclass(frozen=True)
class Proposal:
    schema: str
    path: str
    hazard: str
    before_blob: str
    before_sha256: str
    after_sha256: str
    candidate: bytes
    original_reproducer_required: bool = True
    engineering_qualified: bool = False
    original_owner_admitted: bool = False
    scientific_first_use: bool = False
    autonomous_rsi_proven: bool = False
    deployed: bool = False


def inspect_and_propose(*, path: str, source: bytes, expected_blob: str) -> Proposal:
    """Emit one exact known-shape source proposal, never authorize it."""
    need(path == TARGET and type(expected_blob) is str
         and expected_blob == ORIGINAL_BLOB, "TARGET_SCOPE")
    need(type(source) is bytes and 0 < len(source) <= MAX_SOURCE
         and b"\r" not in source and git_blob(source) == expected_blob,
         "SOURCE_BLOB_DRIFT")
    try:
        original = source.decode("ascii", "strict")
    except UnicodeError as exc:
        raise FalsifierDenied("FORGE_RSI_R13_SOURCE_ENCODING") from exc
    need(original.count(ANCHOR_IMPORT) == 1 and
         original.count(ANCHOR_READER) == 1 and
         'info.Size()>65536' in original and
         'info.Mode().IsRegular()' in original and
         'func readBounded(path string,target any)error{' in original,
         "SOURCE_ANCHOR_OR_GUARD_DRIFT")
    updated = original.replace(ANCHOR_IMPORT, 'import(\n "bytes"\n "crypto/ed25519"\n', 1)
    updated = updated.replace(ANCHOR_READER, REPLACEMENT_READER, 1)
    candidate = updated.encode("ascii")
    need(candidate != source and len(candidate) <= MAX_SOURCE and
         candidate.count(b"decodeBoundedWitness(") == 2,
         "CANDIDATE_NOT_BOUNDED")
    return Proposal(SCHEMA, TARGET, "bounded-json-truncation-after-stat",
                    expected_blob, digest(source), digest(candidate), candidate)


@dataclass(frozen=True)
class Prior:
    task_id: str
    source_family: str
    mechanism: str
    source_sha256: str
    test_sha256: str
    outcome: str
    cohort: str


@dataclass(frozen=True)
class Selection:
    ranked: tuple[str, ...]
    memory_used: bool
    eligible_for_owner: bool = False
    science_accepted: bool = False
    rsi_proven: bool = False


def rank_review_options(*, options: tuple[str, ...], history: tuple[Prior, ...],
                        current_family: str, excluded_task_ids: frozenset[str],
                        use_memory: bool) -> Selection:
    """TRAIN-only advice. Does not run a repair or label it successful.

    Comparing with use_memory=False is the explicit fixed-control ablation.
    Caller-provided history is NOT an authenticated original-owner ledger.
    """
    need(type(options) is tuple and 1 <= len(options) <= 3
         and all(type(s) is str and s in ALLOWED_MECHANISMS for s in options)
         and len(set(options)) == len(options), "OPTION_SET_INVALID")
    need(type(history) is tuple and len(history) <= 128 and
         type(excluded_task_ids) is frozenset
         and all(type(s) is str and 0 < len(s) <= 80 for s in excluded_task_ids)
         and type(current_family) is str and 0 < len(current_family) <= 120
         and type(use_memory) is bool, "HISTORY_SHAPE")
    seen = set()
    scores = {s: 0 for s in options}
    for prior in history:
        need(type(prior) is Prior and
             type(prior.task_id) is str and 0 < len(prior.task_id) <= 80 and
             prior.task_id not in seen and prior.task_id not in excluded_task_ids
             and type(prior.source_family) is str
             and 0 < len(prior.source_family) <= 120
             and prior.source_family != current_family
             and prior.mechanism in ALLOWED_MECHANISMS
             and type(prior.source_sha256) is str
             and type(prior.test_sha256) is str
             and SHA64.fullmatch(prior.source_sha256) is not None
             and SHA64.fullmatch(prior.test_sha256) is not None
             and prior.outcome in ("PASS", "FAIL")
             and prior.cohort == "train", "HISTORY_LEAK_OR_DRIFT")
        seen.add(prior.task_id)
        if use_memory and prior.mechanism in scores:
            scores[prior.mechanism] += 1 if prior.outcome == "PASS" else -1
    # Fully deterministic tie-break follows caller-declared option order.
    order = {name: i for i, name in enumerate(options)}
    return Selection(tuple(sorted(options, key=lambda s: (-scores[s], order[s]))),
                     use_memory and bool(history))
