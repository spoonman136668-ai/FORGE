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
    need(bool(rows) and rows[-1].get("schema") in (
         "forge.f139.source-transition.v27", "forge.f139.source-transition.v28",
         "forge.f139.source-transition.v29", "forge.f139.source-transition.v30", "forge.f139.source-transition.v31", "forge.f139.source-transition.v32", "forge.f139.source-transition.v33")
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


def generation_mechanism():
    """Exact source artifacts used by the typed original-owner generator."""
    root = Path(__file__).resolve().parents[1]
    names = ("promptlineage/lineage.go", "cmd/f139-genenv-source/main.go",
        "f139/nci04_prompt_program.py", "f139/nci04_prompt_source.py",
        "f139/nci04_model_free_search.py", "f139/nci04_genenv_owner_backend.py",
        "f139/nci04_native_contract.py", "f139/nci04_portfolio_source_boundary.py")
    return b"".join(n.encode()+b"\0"+(root/n).read_bytes() for n in names)


def typed_generation_custody(db, source_sha, mechanism_sha256):
    db.verify()
    row = db.conn.execute("SELECT payload FROM events WHERE kind='SOURCE_TRANSITION_ADMITTED' "
                          "ORDER BY seq DESC LIMIT 1").fetchone()
    doc = json.loads(row["payload"]) if row else {}
    need(doc.get("schema") in ("forge.f139.source-transition.v28", "forge.f139.source-transition.v29", "forge.f139.source-transition.v30", "forge.f139.source-transition.v31", "forge.f139.source-transition.v32", "forge.f139.source-transition.v33")
         and doc.get("to_source_sha") == source_sha, "TYPED_RELEASE_NOT_BOUND")
    need(doc.get("generation_mechanism_sha256") == mechanism_sha256, "TYPED_MECHANISM_DRIFT")


def generate_typed_batch(db, *, before, consumed, historical_asts, history_sha256,
                         source_sha, binary, binary_sha):
    """Read-only original-history -> actual existing Go mutation -> source."""
    from f139.nci04_prompt_program import build_plan
    from f139.nci04_prompt_source import compile_prompt_sources, frozen_digest
    mechanism = generation_mechanism()
    typed_generation_custody(db, source_sha, digest(mechanism))
    consumed, historical_asts, sources, eligible_parents = search.consumed_source_identities(
        db, consumed, with_sources=True, with_parent_eligibility=True)
    plan = build_plan(before,history_sources=sources,consumed_sha256=consumed,
        historical_ast_sha256=historical_asts,history_sha256=history_sha256,
        mechanism_sha256=digest(mechanism), eligible_parent_sha256=eligible_parents)
    if plan is None:
        return None
    raw = invoke(binary,binary_sha,plan.request())
    need(generation_mechanism() == mechanism, "TYPED_MECHANISM_CHANGED")
    batch = compile_prompt_sources(raw,result_sha256=digest(raw),frozen=plan.frozen,
        frozen_sha256=frozen_digest(plan.frozen),bindings=plan.bindings,
        bindings_sha256=plan.source_bindings_sha256,mechanism=mechanism,
        mechanism_sha256=digest(mechanism),lane="Yggdrasil",path=search.PATH,
        parent_sha=search.PARENT,before=before,historical_sha256=frozenset(consumed),
        historical_ast_sha256=frozenset(historical_asts))
    return batch


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
    generator = "GENENV_NATIVE_SOURCE_COMPILER"
    marker = " provenance-v1="
    if request is None:
        try:
            batch = generate_typed_batch(db,before=prepared["before"],consumed=consumed,
                historical_asts=historical_asts,history_sha256=prepared["request"]["history_sha256"],
                source_sha=source_sha,binary=binary,binary_sha=binary_sha)
        except BackendUnavailable as exc:
            if str(exc) != "F139_GENENV_TYPED_RELEASE_NOT_BOUND":
                raise
            return {**search.report("GENENV_COMPOSITION_SPACE_EXHAUSTED"),
                    "source_backend_blocked":str(exc)}
        if batch is None:
            return search.report("TYPED_PROGRAM_GRAMMAR_EXHAUSTED")
        generator = "PROMPTBREEDER_TYPED_SOURCE_COMPILER"
        marker = " provenance-prompt-v1="
        projection = batch.bindings_sha256
        projection_name = "source_bindings_sha256"
    else:
        raw = invoke(binary, binary_sha, request)
        root = Path(__file__).resolve().parents[1]
        names = ("genenv/genenv.go", "cmd/f139-genenv-source/main.go",
                 "f139/nci04_genenv_source.py", "f139/nci04_model_free_search.py",
                 "f139/nci04_genenv_owner_backend.py")
        mechanism = b"".join(n.encode()+b"\0"+(root/n).read_bytes() for n in names)
        batch = compile_operator_vectors(raw, result_sha256=digest(raw),
            frozen_sha256=request["frozen_sha256"], history_sha256=request["history_sha256"],
            mechanism=mechanism, mechanism_sha256=digest(mechanism), before=prepared["before"],
            historical_sha256=frozenset(consumed), historical_ast_sha256=frozenset(historical_asts))
        projection = batch.history_sha256
        projection_name = "source_use_history_sha256"
    candidate, _ = batch.candidates[0]
    provenance = dict(generator_result_sha256=batch.generator_result_sha256,
        frozen_sha256=batch.frozen_sha256, **{projection_name:projection},
        original_history_sha256=prepared["request"]["history_sha256"],
        mechanism_sha256=batch.mechanism_sha256, executable_sha256=binary_sha)
    # h binds source-use history for GenEnv or complete source bindings for
    # typed Promptbreeder. o always binds the complete original history.
    compact = dict(r=batch.generator_result_sha256, f=batch.frozen_sha256,
                   h=projection, o=provenance["original_history_sha256"],
                   m=batch.mechanism_sha256, e=binary_sha)
    response = canonical(dict(schema=search.SCHEMA, lane="Yggdrasil", target_commit=search.PARENT,
        path=search.PATH, history_sha256=prepared["request"]["history_sha256"],
        question=candidate.question,
        hypothesis=candidate.hypothesis+marker+canonical(compact).decode("ascii"),
        control="Unmodified frozen parent, original native regression and unfamiliar-family controls; "
                "retain every negative. Source-use projection is not optimizer reward training. "
                "No holdout, scientific first-use, model or policy promotion.",
        candidate_source=candidate.after.decode("utf-8")))
    need(owner_witness() is True, "OWNER_REVOKED")
    result = search.publish_model_once(db, get, steering_get, write,
        session=prepared["session"], raw_response=response, owner_witness=owner_witness)
    return {**result, "generator": generator, "model_calls": 0,
            "paid_model_calls": 0, "source_after_sha256": candidate.after_sha256,
            "generator_result_sha256": batch.generator_result_sha256,
            "provenance": provenance}
