#!/usr/bin/env python3
"""F54 frozen original-FIT-only quantile action feasibility diagnostic.

Prospective protocol ancestor: 1c103be00fd1d807aac657306c573f7b6cc936ef.
No F51/F53 scored seed may be used. No F54 DEV or scientific first-use.
"""
import json
import math
from pathlib import Path
import sys

import numpy as np
import f51_original_acrobot_transfer_dev as f51
import f53_original_acrobot_supported_residual_dev as f53

SCHEMA = "forge.eureka.f54.original-acrobot-fit-quantile-action-audit.v1"
PROTOCOL_COMMIT = "1c103be00fd1d807aac657306c573f7b6cc936ef"
FIT_SHA = "63d31930006ec2f465e4becd989c1a0b922e15a0842ef991fe424074d436a31a"
MODEL_SHA = "968c8353334256634707097ff510bcbee60177253280850f7ed56f7a0c1a93a1"
QUANTILE = .75
ARMS = ("quantile-supported", "momentum-rule", "frozen-fqi",
        "quantile-margin-only", "f53-fixed-margin", "rotated-credit")


def prepare():
    """Original-Farama source and previously consumed book FIT observations only."""
    fit = f53.frozen_fit()
    records, counts, episodes, _ = f51.collect_fit()
    if (len(records) != 8974 or counts != [3604, 1824, 3546] or
        len(episodes) != 48 or f51.digest(records) != FIT_SHA or
        fit["fit_record_sha256"] != FIT_SHA or
        fit["fitted_sha256"] != MODEL_SHA or
        fit["fit_action_counts"] != counts or
        fit["theta"].shape != (3, 15) or
        fit["inverses"].shape != (3, 15, 15) or
        fit["thresholds"].shape != (3,)):
        raise RuntimeError("F54_FROZEN_ORIGINAL_FIT_OR_MODEL_CUSTODY_DRIFT")
    theta = fit["theta"]
    gaps = []
    for row in records:
        phi = f51.features(row[0])
        q = theta @ phi
        h = f51.energy_rule(row[0])
        g = int(np.argmax(q))
        if not np.all(np.isfinite(q)):
            raise RuntimeError("F54_NONFINITE_TRAINING_Q")
        if g != h:
            gap = float(q[g] - q[h])
            if not math.isfinite(gap) or gap <= 0:
                raise RuntimeError("F54_NONPOSITIVE_DISAGREEMENT_MARGIN")
            gaps.append(gap)
    if len(gaps) != 2716:
        raise RuntimeError("F54_PRIOR_F53_FIT_DISAGREEMENT_CUSTODY_DRIFT")
    threshold = float(np.quantile(gaps, QUANTILE))
    if not (math.isfinite(threshold) and 0 < threshold < f53.MARGIN):
        raise RuntimeError("F54_TRAINING_MARGIN_CALIBRATION_INVALID")
    return fit, records, gaps, threshold


class Policy:
    """Public-observation-only, immutable per-FIT-calibration action policy."""
    def __init__(self, kind, theta, inverses, support_thresholds, threshold):
        if kind not in ARMS:
            raise ValueError("F54_UNFROZEN_POLICY")
        self.kind = kind
        self.theta = np.asarray(theta, dtype=np.float64).copy()
        self.inv = np.asarray(inverses, dtype=np.float64).copy()
        self.support = np.asarray(support_thresholds, dtype=np.float64).copy()
        self.margin = float(threshold)
        if (self.theta.shape != (3, 15) or self.inv.shape != (3, 15, 15) or
            self.support.shape != (3,) or
            not all(np.all(np.isfinite(v)) for v in (self.theta, self.inv, self.support)) or
            np.any(self.support <= 0) or
            not math.isfinite(self.margin) or self.margin <= 0):
            raise ValueError("F54_INVALID_FROZEN_FIT")
        self.n = 0

    def action(self, obs):
        h = f51.energy_rule(obs)
        phi = f51.features(obs)
        rows = self.theta[[1, 2, 0]] if self.kind == "rotated-credit" else self.theta
        q = rows @ phi
        if not np.all(np.isfinite(q)):
            raise ValueError("F54_NONFINITE_Q")
        g = int(np.argmax(q))
        if self.kind == "momentum-rule":
            a = h
        elif self.kind == "frozen-fqi":
            a = g
        else:
            margin = f53.MARGIN if self.kind == "f53-fixed-margin" else self.margin
            allowed = g != h and float(q[g] - q[h]) >= margin
            if allowed and self.kind != "quantile-margin-only":
                lg = float(phi @ self.inv[g] @ phi)
                lh = float(phi @ self.inv[h] @ phi)
                if not (math.isfinite(lg) and math.isfinite(lh)):
                    raise ValueError("F54_NONFINITE_ACTION_SUPPORT")
                allowed = lg <= float(self.support[g]) and lh <= float(self.support[h])
            a = g if allowed else h
        if type(a) is not int or a not in (0, 1, 2):
            raise ValueError("F54_INVALID_PUBLIC_ACTION")
        self.n += 1
        return a


def action_audit(records, fit, threshold):
    """No new env is created here; enumerate the *existing* public FIT observations."""
    policies = {k: Policy(k, fit["theta"], fit["inverses"], fit["thresholds"],
                          threshold) for k in ARMS}
    stats = {k: {"deviations": 0, "behavior_matches": 0,
                 "actions": [0, 0, 0]} for k in ARMS}
    support = {"margin_eligible": 0, "both_supported": 0,
               "only_g_supported": 0, "only_h_supported": 0,
               "neither_supported": 0}
    for row in records:
        obs, observed = row[0], int(row[1])
        h = f51.energy_rule(obs)
        phi = f51.features(obs)
        q = fit["theta"] @ phi
        g = int(np.argmax(q))
        if g != h and float(q[g] - q[h]) >= threshold:
            support["margin_eligible"] += 1
            gs = float(phi @ fit["inverses"][g] @ phi) <= float(fit["thresholds"][g])
            hs = float(phi @ fit["inverses"][h] @ phi) <= float(fit["thresholds"][h])
            key = ("both_supported" if gs and hs else "only_g_supported" if gs
                   else "only_h_supported" if hs else "neither_supported")
            support[key] += 1
        for name, policy in policies.items():
            action = policy.action(obs)
            stats[name]["deviations"] += int(action != h)
            stats[name]["behavior_matches"] += int(action == observed)
            stats[name]["actions"][action] += 1
    n = len(records)
    if (any(p.n != n for p in policies.values()) or
        any(sum(v["actions"]) != n for v in stats.values()) or
        support["margin_eligible"] != sum(support[k] for k in (
            "both_supported", "only_g_supported", "only_h_supported",
            "neither_supported")) or
        stats["momentum-rule"]["deviations"] != 0 or
        stats["quantile-margin-only"]["deviations"] != support["margin_eligible"] or
        stats["quantile-supported"]["deviations"] != support["both_supported"] or
        stats["f53-fixed-margin"]["deviations"] != 0):
        raise RuntimeError("F54_FIT_ACTION_OR_PRIOR_F53_NEGATIVE_DRIFT")
    return {"arms": stats, "support": support}


def report():
    fit, records, gaps, threshold = prepare()
    first = action_audit(records, fit, threshold)
    cold = action_audit(records, fit, threshold)
    if f51.digest(first) != f51.digest(cold):
        raise RuntimeError("F54_COLD_ACTION_REPLAY_DRIFT")
    candidate = first["arms"]["quantile-supported"]["deviations"]
    result = {
        "schema": SCHEMA, "prospective_protocol_commit": PROTOCOL_COMMIT,
        "classification": ("F54_FIT_ACTIVATION_UNVERIFIED" if candidate > 0
                           else "F54_FIT_NO_ACTIVATION"),
        "science_accepted": False, "scientific_first_use": False,
        "scored_seeds_accessed": False, "new_transfer_or_retention_evaluations": 0,
        "original_upstream": fit["source"],
        "source_fit_sha256": fit["fit_record_sha256"],
        "trained_fqi_sha256": fit["fitted_sha256"],
        "fit_support_sha256": fit["support_sha256"],
        "fit_observations": len(records), "fit_episodes": len(f51.FIT) * 8,
        "fit_action_counts": fit["fit_action_counts"],
        "raw_fqi_disagreements": len(gaps),
        "margin_calibration_quantile": QUANTILE,
        "margin_calibrated_q_units": threshold,
        "margin_q_gap_min": min(gaps),
        "margin_q_gap_p50": float(np.quantile(gaps, .5)),
        "margin_q_gap_p75": float(np.quantile(gaps, .75)),
        "margin_q_gap_p90": float(np.quantile(gaps, .90)),
        "margin_q_gap_max": max(gaps),
        "support_percentiles": fit["thresholds"].tolist(),
        "audit": first,
        "cold_audit_matches": True
    }
    result["report_sha256"] = f51.digest(result)
    return result


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        raise ValueError("F54_USAGE: python f54_original_acrobot_fit_quantile_action_audit.py /tmp/report.json")
    r = report()
    path = Path(args[0]).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(f51.canonical(r) + b"\n")
    print("F54_FIT_CLASSIFICATION=" + r["classification"])
    print("F54_FIT_ACTIONS=" + json.dumps({
        "threshold_q": r["margin_calibrated_q_units"],
        "raw_fqi_disagreements": r["raw_fqi_disagreements"],
        "candidate_overrides": r["audit"]["arms"]["quantile-supported"]["deviations"],
        "margin_only_overrides": r["audit"]["arms"]["quantile-margin-only"]["deviations"],
        "f53_fixed_overrides": r["audit"]["arms"]["f53-fixed-margin"]["deviations"],
        "support_counts": r["audit"]["support"],
        "report_sha256": r["report_sha256"]}, sort_keys=True))
    return r


if __name__ == "__main__":
    main()
