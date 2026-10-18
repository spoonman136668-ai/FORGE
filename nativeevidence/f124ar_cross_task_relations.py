"""F124-AR prospective cross-task learned causal relationship representations.

Only a caller-supplied sequence of PUBLIC 24-demo tasks may train shared
parameters. The first 20 demonstrations per task are FIT; last four are
CHECK, never shared-weight training. No source adapter, operator grammar,
inverse oracle or evaluator-side paired label is imported here.

Original Yggdrasil 7-active/9-retained predictor stays unmodified. All extra
shared parameters, task examples and feature activations are disclosed.
"""
from __future__ import annotations
import math

import f124aj_example_operator_learner as public
import f124ag_transition_models as transition
import f124q_fresh_source as guard

MODES = (
    "amortized_support_attention",
    "contrastive_relation_binding",
    "bounded_recurrent_inverse",
)
WIDTHS = (8, 16)
FIT, CHECK = 20, 4
VALIDATION_MAX_WRONG_BITS = 12
EPOCHS = 2

def need(valid, label):
    guard.need(valid, "F124AR_LEARNED_" + label)

def signed(bits):
    need(len(bits) == 16 and all(bit in (0, 1) for bit in bits),
         "PUBLIC_SIXTEEN_BITS")
    return tuple(2.0 * bit - 1.0 for bit in bits)

def hidden(x, input_weights):
    return [math.tanh(sum(a * b for a, b in zip(row, x)))
            for row in input_weights]

def decoder(h, output_weights):
    return [math.tanh(sum(a * b for a, b in zip(row, h)))
            for row in output_weights]

def _init(mode, width):
    # Deterministic initial weights; initialization is not an operator catalog.
    offset = MODES.index(mode) + 1
    w1 = [[(((i + 3) * (j + 5) * (offset + 2)) % 23) - 11) / 128.0
           for j in range(16)] for i in range(width)]
    w2 = [[(((i + 7) * (j + 2) * (offset + 3)) % 29) - 14) / 128.0
           for j in range(width)] for i in range(16)]
    return w1, w2

def train_shared(public_tasks, mode, width):
    """Learn shared weights from PUBLIC demonstrations on prequalified TRAIN.

    Caller must pass only sanitized 24-row support lists, NOT source case
    tuples with hidden operator identity/true graph or evaluator labels.
    This function is not invoked by focused qualification.
    """
    need(mode in MODES and width in WIDTHS, "FROZEN_ARCHITECTURES")
    need(isinstance(public_tasks, (list, tuple)) and
         1 <= len(public_tasks) <= 48, "BOUNDED_TRAIN_TASK_COUNT")
    w1, w2 = _init(mode, width)
    steps = 0
    for demonstrations in public_tasks:
        need(type(demonstrations) is list and len(demonstrations) == FIT + CHECK,
             "PUBLIC_SUPPORT_BUDGET")
        for demo in demonstrations:
            signed(demo["output_bits"])
            signed(demo["input_bits"])
    for _ in range(EPOCHS):
        for demonstrations in public_tasks:
            for index, demo in enumerate(demonstrations[:FIT]):
                x = signed(demo["output_bits"])
                y = signed(demo["input_bits"])
                h = hidden(x, w1)
                pred = decoder(h, w2)
                if mode == "contrastive_relation_binding":
                    # Negatives are task-local public FIT inputs, not graph labels.
                    other = signed(demonstrations[(index + 1) % FIT]["input_bits"])
                    err = [y[k] - pred[k] + .15 * (y[k] - other[k])
                           for k in range(16)]
                elif mode == "bounded_recurrent_inverse":
                    intermediate = [math.tanh(.5 * x[k] + .5 * pred[k])
                                    for k in range(16)]
                    err = [y[k] - intermediate[k] for k in range(16)]
                else:
                    err = [y[k] - pred[k] for k in range(16)]
                previous_w2 = [row[:] for row in w2]
                eta = .008
                for k in range(16):
                    for j in range(width):
                        w2[k][j] = max(-2., min(2., w2[k][j] +
                                                eta * err[k] * h[j]))
                for j in range(width):
                    feedback = sum(previous_w2[k][j] * err[k]
                                   for k in range(16)) / 16.
                    for k in range(16):
                        w1[j][k] = max(-2., min(2., w1[j][k] +
                                                eta * feedback * x[k]))
                steps += 16 * width * 4
    return {"mode": mode, "width": width,
            "input_projection": tuple(tuple(row) for row in w1),
            "inverse_decoder": tuple(tuple(row) for row in w2),
            "train_public_tasks": len(public_tasks),
            "public_fit_per_task": FIT,
            "public_check_per_task": CHECK,
            "training_operations_upper": steps,
            "shared_parameters": 32 * width,
            "shared_float_storage_bytes_lower": 32 * width * 8,
            "source_oracle_used": False,
            "operator_catalog_known": False}

def _estimate(shared, encoded, fit):
    mode, width = shared["mode"], shared["width"]
    x = signed(encoded)
    h = hidden(x, shared["input_projection"])
    network = decoder(h, shared["inverse_decoder"])
    if mode == "amortized_support_attention":
        similarities = []
        for demo in fit:
            feature = hidden(signed(demo["output_bits"]),
                             shared["input_projection"])
            dot = sum(a * b for a, b in zip(h, feature)) / width
            similarities.append(dot)
        scale = max(similarities)
        attention = [math.exp(min(0., v - scale)) for v in similarities]
        z = sum(attention)
        support = [sum(attention[i] * signed(d["input_bits"])[k]
                       for i, d in enumerate(fit)) / z for k in range(16)]
        return [(.70 * support[k] + .30 * network[k]) for k in range(16)]
    if mode == "contrastive_relation_binding":
        # Per-bit learned prototype contrast from PUBLIC support labels only.
        xfeatures = [hidden(signed(d["output_bits"]),
                            shared["input_projection"]) for d in fit]
        similarity = [sum(a * b for a, b in zip(h, f)) / width
                      for f in xfeatures]
        output = []
        for k in range(16):
            plus = [similarity[i] for i, d in enumerate(fit)
                    if d["input_bits"][k]]
            minus = [similarity[i] for i, d in enumerate(fit)
                     if not d["input_bits"][k]]
            if not plus or not minus:
                output.append(network[k])
            else:
                output.append(.6 * (max(plus) - max(minus)) +
                              .4 * network[k])
        return output
    # A bounded two-step learned correction; public FIT residuals only.
    bias = [0.] * 16
    for demo in fit:
        raw_h = hidden(signed(demo["output_bits"]),
                       shared["input_projection"])
        raw_output = decoder(raw_h, shared["inverse_decoder"])
        gold = signed(demo["input_bits"])
        for k in range(16):
            bias[k] += (gold[k] - raw_output[k]) / len(fit)
    pred = [math.tanh(.5 * x[k] + .5 * network[k]) for k in range(16)]
    for _ in range(2):
        pred = [math.tanh(.5 * pred[k] + .5 * (network[k] + .5 * bias[k]))
                for k in range(16)]
    return pred

def normalize(graph, shared):
    need(shared["mode"] in MODES and shared["width"] in WIDTHS,
         "FROZEN_SHARED_WEIGHTS")
    need(len(shared["input_projection"]) == shared["width"] and
         len(shared["inverse_decoder"]) == 16, "MODEL_SHAPE")
    raw, demos, task = public.public_task(graph)
    need(len(demos) == FIT + CHECK, "EXACT_20_4_PUBLIC_SUPPORT")
    fit = demos[:FIT]
    wrong_bits = 0
    for demo in demos[FIT:]:
        prediction = _estimate(shared, demo["output_bits"], fit)
        wrong_bits += sum(int((v >= 0) != bool(bit))
                          for v, bit in zip(prediction, demo["input_bits"]))
    accepted = wrong_bits <= VALIDATION_MAX_WRONG_BITS
    inference_queries = CHECK
    if accepted:
        for edge in raw["edges"]:
            pred = _estimate(shared, edge["src_bits"], fit)
            edge["src_bits"] = [int(value >= 0) for value in pred]
            inference_queries += 1
        transition.frozen.prior.parent.validate_15(raw)
    width = shared["width"]
    # Deliberate lower bounds only; actual OS RSS/peak measured by later gate.
    memory = {
        "shared_float_parameters": 32 * width,
        "shared_float_bytes_lower": 32 * width * 8,
        "public_fit_bit_storage_lower": FIT * 32,
        "minimum_feature_activation_float_slots": width * (FIT + 1),
        "extra_task_working_storage_disclosed": True,
        "max_original_cognitive_cells": 16,
    }
    return (raw if accepted else None), {
        "mode": shared["mode"], "width": width,
        "public_fit": FIT, "public_check": CHECK,
        "validation_wrong_bits": wrong_bits,
        "validation_wrong_bit_limit": VALIDATION_MAX_WRONG_BITS,
        "abstained": not accepted,
        "estimated_inference_mul_add_lower":
            inference_queries * (32 * width),
        "source_oracle_used": False,
        "operator_catalog_known": False,
        **memory,
    }

def ygg(graph, base, delta, shared):
    raw, observation = normalize(graph, shared)
    if raw is None:
        return -1.e9, None, observation
    score, original_score, ratio, work = transition.ygg_transition(
        raw, list(base), list(delta), .1)
    need(work["max_active"] <= 7 and work["max_retained"] <= 9,
         "UNMODIFIED_7_ACTIVE_9_RETAINED")
    return score, work, observation
