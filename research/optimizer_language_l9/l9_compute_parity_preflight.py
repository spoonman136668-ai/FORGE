#!/usr/bin/env python3
"""Frozen L9 Transformer compute-parity preflight. Source-only; no model/data imports.

The result is a CONDITIONAL upper bound (all decodes reach the token cap),
not a FLOP, latency, energy or scientific performance measurement.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path

SUITE_BLOB = "710ce648a30ffc55647f689c5f4aa3ac13b07066"
SELECT_BLOB = "91f8108af5e6f3a25e2a8ca07dc3674bd2358f4e"
ROLE_SHA = "b9995c1846f5e1d99bf8bc4083dde0ebb41140906284bcf050a7ed6fe0efe726"
SELECT_EXAMPLES = 2154


def reject(condition: bool, reason: str) -> None:
    if not condition:
        raise ValueError("L9_COMPUTE_PARITY_SOURCE_REJECT:" + reason)


def git_blob(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def find_unique(nodes, name: str, kind) -> ast.AST:
    matches = [x for x in nodes if isinstance(x, kind) and x.name == name]
    reject(len(matches) == 1, "MISSING_OR_DUPLICATE_" + name)
    return matches[0]


def literal_assignments(nodes) -> dict:
    values = {}
    for node in nodes:
        if isinstance(node, ast.Assign) and isinstance(node.value, (ast.Constant, ast.Tuple)):
            try:
                v = ast.literal_eval(node.value)
            except (ValueError, TypeError):
                continue
            for target in node.targets:
                if isinstance(target, ast.Name):
                    values[target.id] = v
    return values


def conditional_bounds(examples: int, seeds: int, epochs: int, max_steps: int):
    for key, value in (("examples", examples), ("seeds", seeds),
                       ("epochs", epochs), ("max_steps", max_steps)):
        reject(type(value) is int and value > 0, "INVALID_" + key)
    evaluations = examples * seeds * epochs
    return {
        "complete_evaluations": evaluations,
        "max_forward_invocations_if_no_early_eos": evaluations * max_steps,
        "max_cumulative_decoder_prefix_tokens_if_no_early_eos":
            evaluations * max_steps * (max_steps + 1) // 2,
        "upper_bound_conditional_on_no_early_eos": True,
    }


def audit(suite_raw: bytes, select_raw: bytes) -> dict:
    reject(git_blob(suite_raw) == SUITE_BLOB, "FROZEN_MODEL_BLOB_DRIFT")
    reject(git_blob(select_raw) == SELECT_BLOB, "FROZEN_SELECT_BLOB_DRIFT")
    suite = ast.parse(suite_raw.decode("utf-8-sig"))
    selector = ast.parse(select_raw.decode("utf-8-sig"))
    main = literal_assignments(suite.body)
    select_consts = literal_assignments(selector.body)
    reject(main.get("MAX_TARGET_BYTES") == 512, "TOKEN_CAP_DRIFT")
    reject(main.get("CHECKPOINT_EPOCHS") == (4, 8, 12), "MODEL_EPOCHS_DRIFT")
    reject(main.get("MANDATORY_SEEDS") == (1701, 1702), "MODEL_SEEDS_DRIFT")
    reject(select_consts.get("ALLOWED_EPOCHS") == (4, 8, 12), "SELECT_EPOCHS_DRIFT")
    reject(select_consts.get("ALLOWED_SEEDS") == (1701, 1702), "SELECT_SEEDS_DRIFT")
    reject(select_consts.get("ROLE_SHA") == ROLE_SHA, "SOURCE_ROLE_DRIFT")
    generator = find_unique(suite.body, "build_transformer_model", ast.FunctionDef)
    klass = find_unique(generator.body, "SmallTransformer", ast.ClassDef)
    decode = find_unique(klass.body, "greedy", ast.FunctionDef)
    forward = find_unique(klass.body, "forward", ast.FunctionDef)
    loops = [n for n in ast.walk(decode) if isinstance(n, ast.For)
             and isinstance(n.iter, ast.Call) and
             isinstance(n.iter.func, ast.Name) and n.iter.func.id == "range"
             and len(n.iter.args) == 1 and isinstance(n.iter.args[0], ast.Name)
             and n.iter.args[0].id == "max_steps"]
    reject(len(loops) == 1, "GREEDY_TOKEN_LOOP_DRIFT")
    loop = ast.unparse(loops[0])
    reject("self.forward(src, token)" in loop, "GREEDY_FULL_FORWARD_DRIFT")
    reject("token = torch.cat([token, nxt], dim=1)" in loop, "PREFIX_GROWTH_DRIFT")
    reject("if bool((nxt == EOS).all())" in loop, "EARLY_EOS_DRIFT")
    fwd = ast.unparse(forward)
    reject("self.transformer(" in fwd and "self._embed(src)" in fwd
           and "self._embed(tgt_in)" in fwd, "ENCODER_RECOMPUTATION_DRIFT")
    infer = find_unique(selector.body, "inference_one", ast.FunctionDef)
    infer_txt = ast.unparse(infer)
    reject("max_steps=model.MAX_TARGET_BYTES + 1" in infer_txt, "INFER_CAP_DRIFT")
    metrics = find_unique(selector.body, "compute_select_metric", ast.FunctionDef)
    metrics_txt = ast.unparse(metrics)
    reject("len(select) == 2154" in metrics_txt and
           "for ex in select" in metrics_txt, "FULL_SELECT_DRIFT")
    runner = find_unique(selector.body, "run", ast.FunctionDef)
    runner_txt = ast.unparse(runner)
    reject("for epoch in ALLOWED_EPOCHS" in runner_txt, "THREE_EPOCHS_DRIFT")
    reject("model.assert_audit_not_used(train + select)" in runner_txt,
           "AUDIT_EXCLUSION_GUARD_DRIFT")
    max_steps = main["MAX_TARGET_BYTES"] + 1
    return {
        "schema": "forge.optimizer.language.l9.frozen-compute-parity-static-v1",
        "model_source_git_blob": SUITE_BLOB,
        "selector_source_git_blob": SELECT_BLOB,
        "source_role_sha256": ROLE_SHA,
        "frozen_examples_per_epoch": SELECT_EXAMPLES,
        "mandatory_seeds": list(main["MANDATORY_SEEDS"]),
        "mandatory_epochs": list(main["CHECKPOINT_EPOCHS"]),
        "max_generated_steps_per_example": max_steps,
        "original_transformer_full_forward_recomputed_each_generated_step": True,
        "original_transformer_src_embedding_and_encoder_recomputed_each_generated_step": True,
        **conditional_bounds(SELECT_EXAMPLES, 2, 3, max_steps),
        "compute_or_energy_measured": False,
        "scientific_quality_measured": False,
        "audit_dev_loaded": False,
        "official_test_loaded": False,
        "disposition": "SOURCE_STATIC_BENCHMARK_COST_PARITY_UNQUALIFIED",
        "interpretation": (
            "Conditional static maximum only. EOS can terminate early, so do not "
            "report these bounds as observed calls, latency, FLOPs or energy. "
            "A future computational Pareto conclusion needs an independently "
            "qualified efficient conventional Transformer baseline, matched "
            "quality and total resource accounting; do not rewrite frozen "
            "checkpoints or reinterpret running L9_SELECT."
        )
    }


def main() -> None:
    root = Path(__file__).resolve().parent
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    report = audit((root / "l9_model_suite.py").read_bytes(),
                   (root / "l9_neural_select_only.py").read_bytes())
    reject(not args.out.exists(), "REFUSE_OVERWRITE")
    args.out.write_bytes((json.dumps(report, sort_keys=True,
                                    separators=(",", ":")) + "\n").encode("utf-8"))
    print("L9_FROZEN_COMPUTE_PARITY_STATIC=PASS")
    print("L9_PARETO_EFFICIENCY_CERTIFIED=FALSE")


if __name__ == "__main__":
    main()
