"""Fresh R8 FIT seed binding for existing original-source training pipeline.

Only call train_sixfield_fit in an explicitly authorized FIT execution.
No heldout worlds are run here.
"""
import k4y_native_affordance as k4y
import k4x_curriculum_intervention as k4x
from k4t_f4_sixfield_conventional import fit as fit_sixfield

FIT=tuple(range(81400,81424))

def train_sixfield_fit():
    old_seeds=k4y.SEEDS
    old_fit=k4x.FIT_SEEDS
    try:
        k4y.SEEDS={**old_seeds,"FIT":FIT}
        stream,starts,audit,wall,control=k4y.fit()
        if control is None or len(stream)!=12000:
            raise ValueError("R8_FIT_SOURCE_NOT_QUALIFIED")
        if len(starts)==0:
            raise ValueError("R8_FIT_EPISODE_CUSTODY_MISSING")
        if any(event.get("family") not in ("empty","fourrooms") or
               type(event.get("action")) is not int or event["action"] not in (0,1,2)
               for event in stream):
            raise ValueError("R8_FIT_EVENT_IDENTITY_OR_ACTION_DRIFT")
        if any(type(event.get("seed")) is not int or event["seed"] not in FIT for event in stream):
            raise ValueError("R8_FIT_STREAM_SEED_CONTAMINATION")
        if any(sum(event["family"]==family for event in stream)!=6000 or
               audit.get(family,{}).get("public_steps")!=6000 or
               audit.get(family,{}).get("episodes_executed",0)<1 or
               audit.get(family,{}).get("distinct_training_seeds",0)<1
               for family in ("empty","fourrooms")):
            raise ValueError("R8_FIT_SOURCE_AUDIT_MISMATCH")
        if any(type(start.get("seed")) is not int or start["seed"] not in FIT or
               start.get("family") not in ("empty","fourrooms") for start in starts):
            raise ValueError("R8_FIT_START_COHORT_DRIFT")
        learned,digest=fit_sixfield(stream)
        return learned,{"fit_seeds":[FIT[0],FIT[-1]],"fit_events":len(stream),
                        "fit_model_sha256":digest,"scientific_accepted":False}
    finally:
        k4y.SEEDS=old_seeds
        k4x.FIT_SEEDS=old_fit
