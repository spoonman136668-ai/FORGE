"""Mass Research: INDEPENDENT source-only R5 causal-event accessibility audit.

Reads the unchanged R5 public developer task and R4 baseline transcript
interface. It does not generate original H1/H2 source, train/retrain a model,
reclassify existing R5 DEV, consume any held first-use, or write authority.
"""
import hashlib
import json
from public_dev import PUBLIC_FAMILIES, canonical
from r5_causal_dev import R5CausalWorld, public_causal_oracle
from r4_public_experience import PublicTranscript

R5_CAUSAL_KINDS=("feed_pulse", "dependence_pulse", "goal_confirmed")
BASELINE_BOUND_KINDS=("relay_pulse","inflow_arrived",
                      "relay_stable","reservoir_balanced")
BASE_SHA="ec2e2d88d06c7c8141949b9858c42c2d77849ff9"
DISPOSITION="R5_R4_EVENT_VOCABULARY_INTERFACE_MISMATCH_DEVELOPMENT_ONLY"


def one_public_trace(family, seed):
    """Reconstruct observer state from PUBLIC events, not private world roles."""
    if family not in PUBLIC_FAMILIES or type(seed) is not int:
        raise ValueError("MASS_R5_PUBLIC_SCOPE_REQUIRED")
    world=R5CausalWorld(family,"DEV-MASS-R5-PUBLIC-AUDIT",seed)
    initial=json.loads(canonical(world.reset()))
    def step(chosen):
        return json.loads(canonical(world.step(chosen)))
    solved=public_causal_oracle(initial,step)
    rows=world.public_trace_records()  # public-only engineering replay
    trace=PublicTranscript(initial)
    counts={kind:0 for kind in R5_CAUSAL_KINDS}
    causal_with_legacy_semantics=0
    legacy_causal_feature_nonzero=0
    causal_events=0
    for row in rows:
        observation=row["result"]["observation"]
        action=row["action"]
        trace.ingest(action,observation)
        new_events=[evt for evt in observation["delayed_events"]
                    if evt.get("kind") in R5_CAUSAL_KINDS]
        for event in new_events:
            counts[event["kind"]]+=1
        if new_events:
            causal_events+=len(new_events)
            # These names are raw PUBLIC events, not privately known roles.
            if (trace.public_ready is not None
                    or trace.public_partial is not None
                    or trace.public_confirmed is not None):
                causal_with_legacy_semantics+=1
            x=trace.features()
            # x[8:20] = ready/partial/confirmed public causal identities.
            # x[23] = R3 event-type recognition flag.
            if any(x[8:20]) or x[23]:
                legacy_causal_feature_nonzero+=1
    if solved["reward"]!=1 or not all(counts.values()):
        raise AssertionError("MASS_R5_PUBLIC_DIAGNOSTIC_OR_EVENT_MISSING")
    digest=hashlib.sha256(canonical([
        [row["action"],row["result"]["observation"]["delayed_events"]]
        for row in rows
    ])).hexdigest()
    return {
        "schema":"mass.r5.independent-public-event-audit.v1",
        "r5_source_parent":BASE_SHA,
        "family":family,"seed":seed,
        "public_task_solvable":True,
        "public_event_counts":counts,
        "number_public_causal_events":causal_events,
        "legacy_transcript_role_bindings_at_causal_events":
            causal_with_legacy_semantics,
        "legacy_causal_feature_nonzero_at_causal_events":
            legacy_causal_feature_nonzero,
        "legacy_public_event_names_recognized":
            sorted(set(R5_CAUSAL_KINDS)&set(BASELINE_BOUND_KINDS)),
        "public_action_event_digest":digest,
        "scientific_first_use":False,
        "learned_cognitive_transfer":"NOT_TESTED",
        "disposition":DISPOSITION,
    }


def audit_public_development(seeds=(31,41,59,83)):
    """A fixed public diagnostic sequence, never an exploratory held search."""
    if tuple(seeds)!=(31,41,59,83):
        raise ValueError("MASS_R5_AUDIT_SEEDS_FROZEN")
    evidence={family:[one_public_trace(family,seed) for seed in seeds]
              for family in PUBLIC_FAMILIES}
    return {
        "schema":"mass.r5.independent-public-interface-audit.v1",
        "candidate_r5_git_head":BASE_SHA,
        "frozen_public_audit_seeds":list(seeds),
        "families":evidence,
        "conclusion":DISPOSITION,
        "qualifies_R5_fully_trained_comparators":False,
        "qualifies_original_H1_H2":False,
        "ckb_plane_admission":"NONE",
    }


if __name__=="__main__":
    print(json.dumps(audit_public_development(),sort_keys=True,separators=(",",":")))
