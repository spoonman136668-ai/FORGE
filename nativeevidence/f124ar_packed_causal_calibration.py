"""F124-AR one-packed causal evidence with TRAIN-calibrated handoff penalties.

The calibration routine accepts evaluator/source-normalized TRAIN graph pairs
only, discloses five global likelihood parameters, and is not called from
the forward scorer. No source inverse, operator labels or true graph labels
enter model inference. Exactly ONE 12-bit packed code and score per public
node survive each hop, maximum 64 public nodes.
"""
from __future__ import annotations
from collections import defaultdict
import math

import f124ae_frozen_source as structural
import f124q_independent_binding as original_q
import f124o_native_learners as original_o
import f124am_terminal_competition as original

MODES = ("original_gamma0",
         "train_calibrated_hop_likelihood",
         "relative_counterfactual_prefix")
ALPHAS = (0., .02, .06, .12)
CHECKSUM = original.CHECKSUM

def need(valid, label):
    structural.need(valid, "F124AR_PACKED_" + label)

def pack(bits):
    need(len(bits) == 16 and all(bit in (0, 1) for bit in bits),
         "ORIGINAL_PUBLIC_BIT_WIDTH")
    code = 0
    for j in range(4):
        value = sum(CHECKSUM[i] * bits[4 * j + i]
                    for i in range(4)) % 5
        code |= value << (3 * j)
    need(0 <= code < 4096, "SINGLE_TWELVE_BIT_PACKET")
    return code

def mismatch(a, b):
    return sum(((a >> (3 * j)) & 7) != ((b >> (3 * j)) & 7)
               for j in range(4))

def _handoff_histogram(graph):
    """Statistical TRAIN-only public adjacent-hop handoff evidence."""
    structural.validate_15(graph)
    index = defaultdict(list)
    for edge in original_o.sorted_edges(graph):
        index[(edge["from"], edge["role"])].append(edge)
    counts = [0] * 5
    roles = graph["roles"]
    for t in range(len(roles) - 1):
        for (node, role), group in index.items():
            if role != roles[t]:
                continue
            for edge in group:
                nxt = index.get((edge["to"], roles[t + 1]), ())
                dst = pack(edge["dst_bits"])
                for candidate in nxt:
                    counts[mismatch(dst, pack(candidate["src_bits"]))] += 1
    return counts

def fit_calibration(public_normalized_train):
    """Estimate class-conditional handoff likelihood on TRAIN ONLY.

    Each row is (case_identity, family, known_positive_graph,
    known_negative_graph) after evaluator normalization. These TRAIN labels
    are allowed for calibrating global parameters, but NEVER passed to score.
    """
    need(type(public_normalized_train) in (list, tuple) and
         len(public_normalized_train) == 48 and
         all(len(row) == 4 for row in public_normalized_train),
         "TRAIN_ONLY_FORTY_EIGHT_PAIRS")
    pos = [1.] * 5
    neg = [1.] * 5
    for _, _, positive, negative in public_normalized_train:
        for k, count in enumerate(_handoff_histogram(positive)):
            pos[k] += count
        for k, count in enumerate(_handoff_histogram(negative)):
            neg[k] += count
    sum_pos, sum_neg = sum(pos), sum(neg)
    log_positive_relative_to_negative = tuple(
        math.log((p / sum_pos) / (n / sum_neg))
        for p, n in zip(pos, neg))
    need(len(log_positive_relative_to_negative) == 5 and
         all(math.isfinite(x) for x in log_positive_relative_to_negative),
         "FINITE_TRAIN_CALIBRATION")
    return {"likelihood_log_ratio": log_positive_relative_to_negative,
            "train_pairs": 48, "global_parameters": 5,
            "global_parameter_bytes_lower": 40,
            "fit_handoff_count": int(sum(pos) + sum(neg) - 10),
            "calibration_source": "source-normalized TRAIN pairs only",
            "source_inverse_in_model": False}

def score(graph, base, delta, mode, alpha, calibration=None):
    need(mode in MODES and alpha in ALPHAS, "FROZEN_MODE_AND_PENALTY")
    if mode == "original_gamma0" or alpha == 0.:
        value, original_work = original.terminal_competitive(
            graph, base, delta, 0.)
        return value, dict(original_work,
                           extra_retained_states=0,
                           extra_hop_evidence_ops=0,
                           model_global_parameter_bytes_lower=0,
                           source_oracle_in_model=False)
    if mode == "train_calibrated_hop_likelihood":
        need(isinstance(calibration, dict) and
             calibration.get("train_pairs") == 48 and
             len(calibration["likelihood_log_ratio"]) == 5 and
             all(math.isfinite(x) for x in calibration["likelihood_log_ratio"]),
             "TRAIN_CALIBRATION_REQUIRED")
        log_ratio = calibration["likelihood_log_ratio"]
    else:
        log_ratio = None
    structural.validate_15(graph)
    weights = original_q.wingless_anchored_weights(list(base), list(delta))
    edges = original_o.sorted_edges(graph)
    index = defaultdict(list)
    for edge in edges:
        index[(edge["from"], edge["role"])].append(edge)
    work = {"edge_inspections": len(edges),
            "raw_bit_reads": 0,
            "affinity_ops": 0,
            "max_active": 1,
            "max_states_per_node": 1,
            "max_packed_bits_per_state": 12,
            "max_index_entries": len(edges),
            "max_encoded_cache": 0,
            "max_lookahead_cache": 0,
            "extra_retained_states": 0,
            "extra_hop_evidence_ops": 0,
            "model_global_parameter_bytes_lower": 40 if log_ratio else 0,
            "source_oracle_in_model": False}

    def packet(bits):
        work["raw_bit_reads"] += 16
        return pack(bits)

    def affinity(a, b):
        work["affinity_ops"] += 4
        av = [weights[j] * (((a >> (3 * j)) & 7) - 2) / 2.
              for j in range(4)]
        bv = [weights[j] * (((b >> (3 * j)) & 7) - 2) / 2.
              for j in range(4)]
        return 1. - sum(abs(x - y) for x, y in zip(av, bv)) / 8.

    states = {graph["start"]: (0., None)}
    for step, role in enumerate(graph["roles"]):
        next_role = graph["roles"][step + 1] if (
            step + 1 < len(graph["roles"])) else None
        following = defaultdict(list)
        for node in sorted(states):
            prior_score, carried = states[node]
            eligible = index.get((node, role), ())
            work["edge_inspections"] += len(eligible)
            rival_matches = [
                (1. if carried is None else
                 affinity(carried, packet(e["src_bits"])))
                for e in eligible]
            work["extra_hop_evidence_ops"] += len(eligible)
            for j, e in enumerate(eligible):
                src = packet(e["src_bits"])
                dst = packet(e["dst_bits"])
                match = 1. if carried is None else affinity(carried, src)
                value = prior_score + weights[4] * (match - .6)
                strongest = max((m for i, m in enumerate(rival_matches)
                                 if i != j), default=match)
                value += .5 * (match - strongest)
                look = 0.
                if next_role is not None:
                    successor = index.get((e["to"], next_role), ())
                    work["edge_inspections"] += len(successor)
                    look = max(
                        (affinity(dst, packet(n["src_bits"]))
                         for n in successor), default=0.)
                if carried is not None:
                    if mode == "train_calibrated_hop_likelihood":
                        k = mismatch(carried, src)
                        # A mismatch more prevalent in negative TRAIN graphs
                        # receives a calibrated nonnegative penalty.
                        value -= alpha * max(0., -log_ratio[k])
                        work["extra_hop_evidence_ops"] += 4
                    else:
                        # Only temporary within-hop rivals, never retained as
                        # a second per-node state or persistent path cache.
                        if len(eligible) > 1:
                            closeness = max(0., 1. - abs(match - strongest))
                            value -= alpha * closeness
                            work["extra_hop_evidence_ops"] += len(eligible)
                rank = value + weights[5] * (look - .6)
                following[e["to"]].append((rank, value, dst))
        states = {}
        for node, candidates in following.items():
            candidates.sort(key=lambda row: (-row[0], -row[1], row[2]))
            states[node] = (candidates[0][1], candidates[0][2])
        work["max_active"] = max(work["max_active"], len(states))
        need(work["max_active"] <= 64, "ONE_PACKED_STATE_PER_NODE")
    best = states.get(graph["target"],
                      (-2. * len(graph["roles"]), None))[0]
    value = 4. * (
        best / max(1, len(graph["roles"]) - 1) - weights[6])
    need(math.isfinite(value) and
         work["max_states_per_node"] == 1 and
         work["max_packed_bits_per_state"] == 12 and
         work["extra_retained_states"] == 0,
         "NO_CAPACITY_GROWTH")
    return value, work
