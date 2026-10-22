"""R5: prospectively corrected PUBLIC-only history masking interface.

Fixes the R4 control-bypass problem for NEW DEV cohorts, without altering
R4 code/results.  Restricted named public view, cloned from public data only.
No world private attributes, original H1/H2 or first-use owner access.
"""
import json
from public_dev import canonical
from r4_public_experience import PublicTranscript, get_action
from r5_causal_dev import R5CausalWorld


def isolated_public_view(transcript, mode="normal"):
    if mode not in ("normal", "erase", "blind_delayed"):
        raise ValueError("R5_UNKNOWN_PUBLIC_HISTORY_MODE")
    obs = json.loads(canonical(transcript.latest_observation))
    if mode != "normal":
        obs["delayed_events"] = []
        obs["observations"] = []
    view = PublicTranscript(obs)
    if mode != "erase":
        view.on = list(transcript.on)
        view.off = list(transcript.off)
        view.ticks_after_act = transcript.ticks_after_act
        view.previous_action = json.loads(canonical(transcript.previous_action))
        if mode == "normal":
            view.public_ready = transcript.public_ready
            view.public_partial = transcript.public_partial
            view.public_confirmed = transcript.public_confirmed
            view.active_events = json.loads(canonical(transcript.active_events))
    # Every decision receives a CLONE; cannot modify the real agent transcript.
    return view


def r5_rollout_public_only(model, family, seed, episode_id, mode="normal"):
    world = R5CausalWorld(family,episode_id,seed)
    obs = json.loads(canonical(world.reset()))
    history = PublicTranscript(obs)
    memory = model.init_state()
    for _ in range(41):
        view = isolated_public_view(history,mode)
        # For erasure genuinely kill any model-owned state across actions;
        # masking only the numeric feature vector was insufficient in R4.
        if mode == "erase":
            memory = model.init_state()
        x = view.features()
        label, memory = model.choose(x,view,memory)
        act = get_action(obs,label)
        res = json.loads(canonical(world.step(act)))
        obs = res["observation"]
        history.ingest(act,obs)
        if res["done"]:
            receipt = world.public_trace_receipt()
            invalid = any(e.get("kind")=="invalid_action" for e in obs["observations"])
            return {"reward":int(res["reward"]), "steps":receipt["steps"],
                    "legal":not invalid, "trace_sha256":receipt["trace_head_sha256"]}
    raise RuntimeError("R5_ACTION_CAP_NOT_ENFORCED")
