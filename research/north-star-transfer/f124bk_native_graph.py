"""F124-BK: source-blind learned inverse in the unchanged native graph scorer.

Nonprotected negative synthetic fixtures -940/-939 ONLY. Public 48 support
pairs -> frozen fit -> inverse edge src bits -> original seven-active,
nine-retained Yggdrasil graph transition. Frozen AZ runs on the identical
native graph. Generated graph is an engineering fixture, NOT independent OOD.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
NATIVE = ROOT / "nativeevidence"
AZ_BLOB = "0122190aa3a0972ffb4a709bc1bdd8179c8ba6c7"
AG_BLOB = "94d2ae8266da792d254ac54baf3056bbd9b49412"
KERNEL_BLOB = "bf81ed56cc0daa2c413ad7d9c698969f92befe3d"
MODEL_PRIOR = bytes.fromhex("5a00cd00")
NATIVE_BASE = [0.4, 0.9, 0.65, 0.75, 0.8, 0.2, -0.5]
NATIVE_DELTA = [0.0, 0.0]
NONCE = "b124c0def00d"


def need(ok, code):
    if not ok:
        raise RuntimeError("F124BK_NATIVE_" + code)


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    need(spec is not None and spec.loader is not None, "IMPORT")
    obj = importlib.util.module_from_spec(spec)
    sys.modules[name] = obj
    spec.loader.exec_module(obj)
    return obj


def sha256_public(rows):
    return hashlib.sha256(json.dumps(
        rows, separators=(",", ":"), sort_keys=True).encode()).hexdigest()


def git_blob(path):
    import subprocess
    p = subprocess.run(
        ["git", "rev-parse", "HEAD:" +
         str(path.relative_to(ROOT)).replace("\\", "/")],
        cwd=ROOT, text=True, capture_output=True)
    need(p.returncode == 0, "GIT_OBJECT_IDENTITY")
    return p.stdout.strip()


def verify_origins():
    need(git_blob(NATIVE / "f124az_joint_public_inverse.py") == AZ_BLOB
         and git_blob(NATIVE / "f124ag_transition_models.py") == AG_BLOB
         and git_blob(HERE / "20261018-mass-learned-kernel.py") ==
         KERNEL_BLOB, "IMMUTABLE_NATIVE_FOUNDATIONS")
    for tag, blob in (("u", "6fe6b5bbece936bb0dfca97c0a8b454918067a19"),
                      ("r", "02997a32ffb3fec60073b3b725cfd0aecae4b1f8")):
        need(git_blob(HERE / ("f124bh_" + tag + "_family.py")) == blob,
             "FROZEN_NEGATIVE_SOURCE_" + tag)
    return True


def bits16(value):
    need(type(value) is int and 0 <= value < 65536, "BITS16")
    return [(value >> j) & 1 for j in range(16)]


def int16(bits):
    need(type(bits) is list and len(bits) == 16
         and all(type(b) is int and b in (0, 1) for b in bits),
         "PUBLIC_16_BIT_ARRAY")
    return sum(b << j for j, b in enumerate(bits))


def source_public(tag):
    need(tag in ("U", "R"), "SEALED_OR_UNREGISTERED_SOURCE")
    file = "f124bh_u_family.py" if tag == "U" else "f124bh_r_family.py"
    s = module("f124bk_negative_" + tag, HERE / file)
    public, _private = s.fixture(-940 if tag == "U" else -939)
    fit, check = public["FIT"], public["CHECK"]
    need(len(fit) == 40 and len(check) == 8
         and public["source_family_sent_to_model"] is False,
         "PUBLIC_40_PLUS_8_NO_TAG")
    return fit, check


def public_native_graph(fit, check):
    """Build native-format *engineering-only* graph from public 48.

    Matching between adjacent edges uses only public x/y values. No source
    truth, oracle operator, private recipe, hidden target label or protected
    task source is ever read. Topology here is NOT a new scientific sample.
    """
    rows = fit + check
    need(len(fit) == 40 and len(check) == 8 and len(rows) == 48,
         "PUBLIC_SUPPORT_EXACT")
    roles = [f"rel_task_{NONCE}:hop{i}" for i in range(7)]
    edges = []
    for i, role in enumerate(roles):
        x, y = rows[i]
        next_x = rows[i + 1][0]
        edges.append({"from":f"n{i}", "to":f"n{i+1}",
                      "role":role, "src_bits":bits16(y),
                      "dst_bits":bits16(next_x)})
    for i in range(5):
        # Public-only distractors; no privileged oracle truth.
        x, y = rows[i + 16]
        edges.append({"from":f"d{i}", "to":f"e{i}",
                      "role":roles[i], "src_bits":bits16(y),
                      "dst_bits":bits16(x)})
    demos = [{"input_bits":bits16(x), "output_bits":bits16(y)}
             for x, y in rows[:24]]
    graph={"start":"n0","target":"n7","roles":roles,"edges":edges,
           "demos":demos}
    need(len(graph["edges"]) == 12 and len(graph["roles"]) == 7,
         "NATIVE_12_EDGES_7_ROLES")
    return graph


def origin_controls():
    sys.path.insert(0, str(NATIVE))
    import f124az_joint_public_inverse as old
    import f124ag_transition_models as native
    import f124aj_example_operator_learner as parser
    kernel=module("bk_frozen_inverse", HERE / "20261018-mass-learned-kernel.py")
    return old, native, parser, kernel


def evaluate(arm, tag, source=None):
    need(arm in ("learned", "AZ") and tag in ("U", "R"),
         "ORIGINAL_SCOPE_ONLY")
    verify_origins()
    old, native, parser, kernel = origin_controls()
    fit, check = source if source is not None else source_public(tag)
    native_graph = public_native_graph(fit, check)
    demos = [{"input_bits":bits16(x),"output_bits":bits16(y)}
             for x,y in fit+check]
    parsed, support, nonce = parser.public_task(native_graph)
    need(support == demos[:24] and nonce == NONCE,
         "NATIVE_PUBLIC_DEMONSTRATION_IDENTITY")
    native.frozen.prior.parent.validate_15(parsed)
    data_digest=sha256_public(fit+check)
    graph_digest=sha256_public(native_graph)
    if arm == "learned":
        model, fit_receipt=kernel.fit_public(fit, check, init=MODEL_PRIOR)
        need(len(model) == 4
             and fit_receipt["public_forward_evaluations"] == 2608,
             "TRAINED_SHARED_SOURCEBLIND_PRIOR")
        edge_ops=0
        for edge in parsed["edges"]:
            decoded=kernel.inverse(int16(edge["src_bits"]), model)
            edge["src_bits"] = bits16(decoded)
            edge_ops += 1
        native.frozen.prior.parent.validate_15(parsed)
        val, raw, ratio, work=native.ygg_transition(
            parsed, list(NATIVE_BASE), list(NATIVE_DELTA), .1)
        need(math.isfinite(val) and work["max_active"] <= 7
             and work["max_retained"] <= 9,
             "FROZEN_NATIVE_COGNITION_BOUNDS")
        outcome={"native_score":val,"native_raw":raw,
                 "native_ratio":ratio, "graph_work":work,
                 "edge_inverse_calls":edge_ops,
                 "model_parameters_bits_lower":32,
                 "fit_errors":fit_receipt["public_FIT_bit_errors"],
                 "CHECK_errors":fit_receipt["public_CHECK_bit_errors"],
                 "original_native_scorer_invoked":True,
                 "source_oracle_seen":False}
    else:
        fitted=old.train(demos, "F124BK-PUBLIC-ENGINEERING-ONLY", 0)
        value, work, diag=old.score(native_graph, list(NATIVE_BASE),
                                    list(NATIVE_DELTA), fitted, demos)
        outcome={"native_score":value, "graph_work":work,
                 "original_native_scorer_invoked":work is not None,
                 "route":fitted["choice"],
                 "AZ_model_bits_lower":fitted["extra_task_model_bits_lower"],
                 "graph_diagnostic":diag,
                 "source_oracle_seen":False}
        if work is not None:
            need(work["max_active"] <= 7 and work["max_retained"] <= 9,
                 "AZ_NATIVE_COGNITION_BOUNDS")
    return {"schema":"mass.f124bk.native-graph-synthetic-task.v1",
            "arm":arm, "tag":tag,
            "same_public_48_sha256":data_digest,
            "same_public_graph_sha256":graph_digest,
            "native_graph_roles":7,"native_graph_edges":12,
            "source_private_or_operator_visible":False,
            "native_Yggdrasil_7_active_9_retained":True,
            "native_path_evidence":outcome,
            "registered_TRAIN_reexecuted":False,
            "protected_U_or_R_generated":False,
            "scientific_accepted":False,
            "whole_resource_parity_qualified":False}
