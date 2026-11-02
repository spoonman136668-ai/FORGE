"""Original-tick GenEnv adapter; no second controller and no inference.

The executable is usable only when its hash was bound by the guarded source
release in the original ledger. The utility receives source-use metadata only,
never credentials, candidate Python, sealed material or scientific authority.
"""
import itertools
import json
import os
from pathlib import Path
import re
import stat
import subprocess

from f139 import nci04_model_free_search as search
from f139.nci04_genenv_source import compile_operator_vectors, source_for_vector
from f139.nci04_native_contract import canonical, digest


class BackendUnavailable(ValueError):
    pass


def need(ok, reason):
    if not ok:
        raise BackendUnavailable("F139_GENENV_" + reason)


def go_digest(domain, obj):
    # Fixed Go struct field order, ASCII-only identifiers and bounded integers.
    raw = json.dumps(obj, separators=(",", ":"), ensure_ascii=True).encode("ascii")
    return digest(domain.encode("ascii") + b"\n" + raw)


def build_request(before, consumed, historical_asts, owner_history_sha256):
    need(type(owner_history_sha256) is str and
         re.fullmatch(r"[0-9a-f]{64}", owner_history_sha256), "OWNER_HISTORY_IDENTITY")
    catalog = {}
    for vector in itertools.product((0, 1), repeat=len(search.OPERATORS)):
        if not any(vector):
            continue
        raw, _ = source_for_vector(before, vector)
        catalog[vector] = (digest(raw), search.normalized(raw))
    used = {v for v, (raw_hash, ast_hash) in catalog.items()
            if raw_hash in consumed or ast_hash in historical_asts}
    need(all(tuple(int(i == j) for i in range(3)) in used for j in range(3)),
         "STANDALONE_CATALOG_NOT_EXHAUSTED")
    fresh = [v for v in catalog if sum(v) >= 2 and v not in used]
    if not fresh:
        return None
    records = []
    for vector in sorted(used):
        raw_hash, ast_hash = catalog[vector]
        # This is a source-consumption projection, NOT a relabeling of native
        # outcomes or optimizer training rewards. The complete original
        # positive/negative/invalid history remains bound by the external pin.
        evidence = digest(canonical({"owner_history_sha256": owner_history_sha256,
            "source_sha256": raw_hash, "ast_sha256": ast_hash, "vector": list(vector)}))
        records.append(dict(sequence=len(records)+1, evidence_sha256=evidence,
                            training_only=True, classification="CONSUMED_INDETERMINATE",
                            vector=list(vector)))
    history = dict(schema="forge.genenvironment.training-history.v1", lane="Yggdrasil",
                   source_sha=search.PARENT, records=records)
    hp = go_digest("FORGE-GENENV-HISTORY-V1", history)
    requests = [dict(id="source-"+"".join(map(str, v)), changes=[
        dict(index=i, delta=1) for i, enabled in enumerate(v) if enabled]) for v in fresh]
    frozen = dict(schema="forge.genenvironment.frozen.v1", lane="Yggdrasil",
                  source_sha=search.PARENT, epoch=len(used)+1, history_sha256=hp,
                  base=[0, 0, 0], max_level=1, max_candidates=len(fresh),
                  max_operations=sum(sum(v) for v in fresh), requests=requests)
    fp = go_digest("FORGE-GENENV-FROZEN-V1", frozen)
    return dict(frozen=frozen, frozen_sha256=fp, history=history, history_sha256=hp)


def executable_custody(db, source_sha):
    db.verify()
    need(db.meta()["source_sha"] == source_sha, "SOURCE_DRIFT")
    rows = [json.loads(r["payload"]) for r in db.conn.execute(
        "SELECT payload FROM events WHERE kind='SOURCE_TRANSITION_ADMITTED' ORDER BY seq")]
    need(bool(rows) and rows[-1].get("schema") == "forge.f139.source-transition.v27"
         and rows[-1].get("to_source_sha") == source_sha, "RELEASE_NOT_BOUND")
    expected = rows[-1].get("genenv_executable_sha256")
    need(type(expected) is str and re.fullmatch(r"[0-9a-f]{64}", expected), "BINARY_PIN")
    root = db.filename.parent
    binary = root / "genenv-source" / source_sha / "f139-genenv-source.exe"
    current = root
    for component in binary.relative_to(root).parts:
        current = current / component
        need(not current.is_symlink(), "EXECUTABLE_SYMLINK")
    info = binary.stat()
    need(stat.S_ISREG(info.st_mode) and 0 < info.st_size <= 16_000_000,
         "EXECUTABLE_FILE")
    need(digest(binary.read_bytes()) == expected, "EXECUTABLE_DRIFT")
    return binary, expected


def invoke(binary, expected_sha256, request):
    need(digest(binary.read_bytes()) == expected_sha256, "EXECUTABLE_DRIFT")
    # No inherited API token, owner key, PATH, proxy or model credentials.
    env = {key: os.environ[key] for key in ("SystemRoot", "WINDIR", "TEMP", "TMP")
           if key in os.environ}
    try:
        completed = subprocess.run([str(binary)], input=canonical(request),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env,
            cwd=str(binary.parent), timeout=15, check=False)
    except (subprocess.SubprocessError, OSError) as exc:
        raise BackendUnavailable("F139_GENENV_UTILITY_UNAVAILABLE") from exc
    need(completed.returncode == 0 and 0 < len(completed.stdout) <= 256_000
         and len(completed.stderr) <= 4096, "UTILITY_FAILED")
    need(digest(binary.read_bytes()) == expected_sha256, "EXECUTABLE_CHANGED")
    return completed.stdout


def publish_after_exhaustion(db, get, steering_get, write, *, prepared, consumed,
                             historical_asts, source_sha, owner_witness):
    try:
        binary, binary_sha = executable_custody(db, source_sha)
    except BackendUnavailable as exc:
        if str(exc) != "F139_GENENV_RELEASE_NOT_BOUND":
            raise
        return {**search.report("MODEL_FREE_SEARCH_EXHAUSTED_NO_FRESH_CANDIDATE"),
                "source_backend_blocked": str(exc)}
    need(callable(owner_witness) and owner_witness() is True, "OWNER_REVOKED")
    request = build_request(prepared["before"], consumed, historical_asts,
                            prepared["request"]["history_sha256"])
    if request is None:
        return search.report("GENENV_COMPOSITION_SPACE_EXHAUSTED")
    raw = invoke(binary, binary_sha, request)
    root = Path(__file__).resolve().parents[1]
    files = ("genenv/genenv.go", "cmd/f139-genenv-source/main.go",
             "f139/nci04_genenv_source.py", "f139/nci04_model_free_search.py",
             "f139/nci04_genenv_owner_backend.py")
    mechanism = b"".join(name.encode()+b"\0"+(root/name).read_bytes() for name in files)
    batch = compile_operator_vectors(raw, result_sha256=digest(raw),
        frozen_sha256=request["frozen_sha256"], history_sha256=request["history_sha256"],
        mechanism=mechanism, mechanism_sha256=digest(mechanism), before=prepared["before"],
        historical_sha256=frozenset(consumed), historical_ast_sha256=frozenset(historical_asts))
    candidate, _ = batch.candidates[0]
    provenance = dict(generator_result_sha256=batch.generator_result_sha256,
        frozen_sha256=batch.frozen_sha256, source_use_history_sha256=batch.history_sha256,
        original_history_sha256=prepared["request"]["history_sha256"],
        mechanism_sha256=batch.mechanism_sha256, executable_sha256=binary_sha)
    # Compact, explicit key map fits the existing immutable 600-character
    # research-text contract without dropping any upstream source identity.
    # r=result, f=frozen, h=source-use history, o=original history,
    # m=mechanism, e=executable.
    compact = dict(r=batch.generator_result_sha256, f=batch.frozen_sha256,
                   h=batch.history_sha256, o=provenance["original_history_sha256"],
                   m=batch.mechanism_sha256, e=binary_sha)
    response = canonical(dict(schema=search.SCHEMA, lane="Yggdrasil", target_commit=search.PARENT,
        path=search.PATH, history_sha256=prepared["request"]["history_sha256"],
        question=candidate.question,
        hypothesis=candidate.hypothesis+" provenance-v1="+canonical(compact).decode("ascii"),
        control="Unmodified frozen parent, original native regression and unfamiliar-family controls; "
                "retain every negative. Source-use projection is not optimizer reward training. "
                "No holdout, scientific first-use, model or policy promotion.",
        candidate_source=candidate.after.decode("utf-8")))
    need(owner_witness() is True, "OWNER_REVOKED")
    result = search.publish_model_once(db, get, steering_get, write,
        session=prepared["session"], raw_response=response, owner_witness=owner_witness)
    return {**result, "generator": "GENENV_NATIVE_SOURCE_COMPILER", "model_calls": 0,
            "paid_model_calls": 0, "source_after_sha256": candidate.after_sha256,
            "generator_result_sha256": batch.generator_result_sha256,
            "provenance": provenance}
