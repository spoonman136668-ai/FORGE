"""ITD-01 R4 PUBLIC demonstration traces, token encoding and rollout interface.

All student observations and teacher examples are PUBLIC action/result bytes.
Never supply a PublicCausalDevWorld object as a learner input.
"""
import hashlib
import json
import random
import time
from public_dev import PUBLIC_FAMILIES, action, canonical
from public_dev_r3 import PublicCausalDevWorld, solve_from_public_only

N_ACT = 10     # 4 activate, 4 deactivate, wait, commit
N_INPUT = 24


class PublicTranscript:
    def __init__(self, first_observation):
        self.names = sorted(x["id"] for x in first_observation["entities"])
        if len(self.names) != 4 or len(set(self.names)) != 4:
            raise ValueError("ITD01_R4_PUBLIC_ENTITIES")
        self.family_on = first_observation["entities"][0]["legal_values"][0]
        self.family_off = first_observation["entities"][0]["legal_values"][1]
        self.on = [0] * 4
        self.off = [0] * 4
        self.ticks_after_act = 0
        self.previous_action = None
        self.public_ready = None
        self.public_partial = None
        self.public_confirmed = None
        self.latest_observation = first_observation
        self.active_events = []

    def ingest(self, chosen, observation):
        self.previous_action = chosen
        if chosen["verb"] == "intervene":
            ix = self.names.index(chosen["target"])
            if chosen["value"] == self.family_on:
                self.on[ix] += 1
            else:
                self.off[ix] += 1
            self.ticks_after_act = 0
        elif chosen["verb"] == "wait":
            self.ticks_after_act += 1
        self.latest_observation = observation
        self.active_events = observation.get("delayed_events", [])
        for event in self.active_events:
            entity = event.get("entity")
            if entity not in self.names:
                raise ValueError("ITD01_R4_EVENT_TARGET_NOT_PUBLIC")
            if event.get("kind") in ("relay_pulse", "inflow_arrived"):
                if event.get("status") == "ready":
                    self.public_ready = entity
                elif event.get("status") == "partial":
                    self.public_partial = entity
            elif event.get("kind") in ("relay_stable", "reservoir_balanced"):
                self.public_confirmed = entity

    def features(self, observation=None):
        observation = self.latest_observation if observation is None else observation
        x = []
        x += [min(2, n) / 2. for n in self.on]
        x += [min(2, n) / 2. for n in self.off]
        x += [float(self.public_ready == n) for n in self.names]
        x += [float(self.public_partial == n) for n in self.names]
        x += [float(self.public_confirmed == n) for n in self.names]
        x += [min(self.ticks_after_act, 4) / 4., min(observation["turn"], 40)/40.]
        x += [float(self.family_on == "fill"),
              float(any(e.get("kind") in ("relay_pulse", "inflow_arrived") for e in self.active_events))]
        assert len(x) == N_INPUT, len(x)
        return x

    def memory_key(self):
        return (
            tuple(min(2,x) for x in self.on),
            tuple(min(2,x) for x in self.off),
            min(self.ticks_after_act, 4),
            self.names.index(self.public_ready) if self.public_ready else -1,
            self.names.index(self.public_partial) if self.public_partial else -1,
            self.family_on,
        )


def get_action(obs, label):
    names = sorted(e["id"] for e in obs["entities"])
    if label == 8:
        return action("wait")
    if label == 9:
        return action("commit")
    return action("intervene", names[label % 4],
                  obs["entities"][0]["legal_values"][0 if label < 4 else 1])


def action_label(public_obs, act):
    names = sorted(e["id"] for e in public_obs["entities"])
    v = act["verb"]
    if v == "wait":
        return 8
    if v == "commit":
        return 9
    if v != "intervene" or act["target"] not in names:
        raise ValueError("ITD01_R4_TEACHER_UNSUPPORTED_PUBLIC_ACTION")
    ix=names.index(act["target"])
    values=public_obs["entities"][0]["legal_values"]
    if act["value"] not in values:
        raise ValueError("ITD01_R4_TEACHER_VALUE_UNRECOGNIZED")
    return ix + 4 * int(act["value"] == values[1])


def sample_trajectory(family, episode_id, seed):
    world = PublicCausalDevWorld(family, episode_id, seed)
    init_obs = world.reset()
    # The public-only teacher already owns reset; its navigation algorithm
    # expects to call reset exactly once. Replay via a PUBLIC state-only wrapper.
    class PublicResetProxy:
        def __init__(self, world, initial):
            self._world = world
            self._initial = initial
        def reset(self):
            return json.loads(canonical(self._initial))
        def step(self, public_action):
            return self._world.step(public_action)
    final = solve_from_public_only(PublicResetProxy(world,init_obs))
    if final["reward"] != 1:
        raise ValueError("ITD01_R4_PUBLIC_TEACHER_FAILED_"+family)
    tr=PublicTranscript(init_obs)
    rows=[]
    prev_obs=init_obs
    for record in world.public_trace_records():
        public_action=record["action"]
        y=action_label(prev_obs,public_action)
        rows.append({"x":tr.features(prev_obs),"key":tr.memory_key(),"y":y})
        obs=record["result"]["observation"]
        tr.ingest(public_action,obs)
        prev_obs=obs
    if rows[-1]["y"] != 9 or not world.public_trace_receipt()["done"]:
        raise ValueError("ITD01_R4_INCOMPLETE_TRACE")
    return {"rows":rows, "public_sha":world.public_trace_receipt()["trace_head_sha256"]}


def public_training(seed, count_per_family):
    rng=random.Random(seed+144)
    pairs=[]
    hash_bytes=hashlib.sha256(b"ITD01_R4_PUBLIC_TRAIN").digest()
    for i,family in enumerate(PUBLIC_FAMILIES):
        for j in range(count_per_family):
            reset_seed=400000 + seed*10000 + i*100000 + j
            t=sample_trajectory(family,f"DEV-R4-TRAIN-{seed}-{i}-{j}",reset_seed)
            pairs.append(t["rows"])
            hash_bytes=hashlib.sha256(hash_bytes + bytes.fromhex(t["public_sha"])).digest()
    rng.shuffle(pairs)
    return pairs,hash_bytes.hex()


def rollout(agent,family,seed,episode_id,history_mode="normal"):
    world=PublicCausalDevWorld(family,episode_id,seed)
    obs=world.reset()
    history=PublicTranscript(obs)
    state=agent.init_state()
    for _ in range(41):
        x=history.features(obs)
        if history_mode == "erase":
            x=[0.0]*len(x)
        elif history_mode == "blind_delayed":
            x=x[:8]+[0.0]*12+x[20:]
        label,state=agent.choose(x,history,state)
        act=get_action(obs,label)
        outcome=world.step(act)
        obs=outcome["observation"]
        history.ingest(act,obs)
        if outcome["done"]:
            receipt=world.public_trace_receipt()
            return {"reward":int(outcome["reward"]),
                    "steps":receipt["steps"],
                    "trace_sha256":receipt["trace_head_sha256"],
                    "legal":not any(e.get("kind")=="invalid_action" for e in obs["observations"])}
    raise ValueError("ITD01_R4_DEV_ACTION_CAP_BYPASS")


def eval_agent(agent,seed,count_per_family,mode,split="challenge"):
    if split not in ("validation","challenge"):
        raise ValueError("ITD01_R4_DEV_SPLIT_INVALID")
    intervention = ("erase" if mode=="erase" else
                    "blind_delayed" if mode=="blind_delayed" else "normal")
    out={}
    for fi,family in enumerate(PUBLIC_FAMILIES):
        samples=[rollout(agent,family,(920000 if split=="validation" else 1720000)
                         +seed*10000+fi*100000+i,
                         f"DEV-R4-{split}-{mode}-{seed}-{fi}-{i}",
                         intervention)
                 for i in range(count_per_family)]
        out[family]={"n":len(samples),
                     "success":sum(x["reward"] for x in samples)/len(samples),
                     "legal_fraction":sum(x["legal"] for x in samples)/len(samples),
                     "mean_actions":sum(x["steps"] for x in samples)/len(samples),
                     "public_rewards_sha256":hashlib.sha256(canonical([x["reward"] for x in samples])).hexdigest(),
                     "public_trace_sha256":hashlib.sha256(canonical([x["trace_sha256"] for x in samples])).hexdigest()}
    return out
