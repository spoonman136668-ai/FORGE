"""Public-only ITD-01 R5: three-stage interactive, delayed causal DEV worlds.

Nothing here is an independently born hidden H1/H2 task. A DEV agent only
receives observation dictionaries and step() callbacks; in-process Python
world instances are never considered secure isolation.
"""
import hashlib
import json
from public_dev import PublicDevWorld, PUBLIC_FAMILIES, MAX_INTERACTIONS, canonical, action


class R5CausalWorld(PublicDevWorld):
    """Independent role order source -> relay -> sink, one irrelevant decoy.

    A: a single source pulse enables relay.
    B: two source pulses enable relay; relay then enables sink.
    All causal status is public only after a delayed intervention.
    """

    def __init__(self, family, episode_id, seed):
        super().__init__(family, episode_id, seed)
        self._source, self._relay, self._sink, self._decoy = self._rng.sample(range(4), 4)
        self._required = frozenset()     # inspect is deliberately uninformative
        self._source_units = 0
        self._source_ready = False
        self._relay_ready = False
        self._completed = False
        self._relay_armed_at_action = False
        self._sink_armed_at_action = False

    def _advance(self):
        self._tick += 1
        arrived = [(idx, active) for due, idx, active in self._pending if due <= self._tick]
        self._pending = [v for v in self._pending if v[0] > self._tick]
        self._last_event = []
        for idx, active in arrived:
            self._confirmed[idx] = active
            if not active:
                if idx == self._source:
                    self._source_units = 0
                    self._source_ready = False
                    self._relay_ready = False
                    self._completed = False
                elif idx == self._relay:
                    self._relay_ready = False
                    self._completed = False
                elif idx == self._sink:
                    self._completed = False
                continue
            if idx == self._source:
                self._source_units += 1
                self._source_ready = (self._source_units >=
                    (1 if self._family == PUBLIC_FAMILIES[0] else 2))
                self._last_event.append({"kind":"feed_pulse",
                    "entity":self._labels[self._relay],
                    "status":"ready" if self._source_ready else "partial"})
            elif idx == self._relay and self._relay_armed_at_action:
                self._relay_ready = True
                self._last_event.append({"kind":"dependence_pulse",
                    "entity":self._labels[self._sink], "status":"ready"})
            elif idx == self._sink and self._sink_armed_at_action:
                self._completed = True
                self._last_event.append({"kind":"goal_confirmed",
                    "entity":self._labels[self._sink], "status":"settled"})
            elif self._rng.random() < 0.4:
                # Noncausal distractor has a different PUBLIC event type.
                # The evaluator never marks it as a causal diagnostic.
                self._last_event.append({"kind":"ambient_drift",
                    "entity":self._labels[self._rng.randrange(4)],"status":"idle"})

    def _success(self):
        return (self._source_ready and self._relay_ready and self._completed
                and not self._pending
                and all(self._states[i] for i in
                        (self._source, self._relay, self._sink))
                and not self._states[self._decoy])

    def step(self, proposed):
        if type(proposed) is dict and proposed.get("verb") == "intervene":
            target = proposed.get("target")
            val = proposed.get("value")
            if target == self._labels[self._relay]:
                self._relay_armed_at_action = bool(
                    self._source_ready and self._states[self._source]
                    and val in ("activate", "fill"))
            if target == self._labels[self._sink]:
                self._sink_armed_at_action = bool(
                    self._relay_ready and self._states[self._relay]
                    and val in ("activate", "fill"))
        return super().step(proposed)


def public_causal_oracle(reset, step):
    """PUBLIC-only intervention discovery. No world object or private fields."""
    labels = sorted(e["id"] for e in reset["entities"])
    legal = reset["entities"][0]["legal_values"]
    if len(labels) != 4 or legal[0] not in ("activate", "fill"):
        raise RuntimeError("R5_PUBLIC_ACTION_CATALOGUE_INVALID")
    put, undo = legal
    found_relay = None
    source = None
    status = None
    # Three waits cover max device arrival latency; stop only on causal kind.
    for candidate in labels:
        step(action("intervene",candidate,put))
        for _ in range(3):
            result = step(action("wait"))
            for event in result["observation"]["delayed_events"]:
                if event.get("kind") == "feed_pulse":
                    found_relay = event["entity"]
                    status = event["status"]
                    source = candidate
        if source is not None:
            break
        step(action("intervene",candidate,undo))
    if source is None:
        return step(action("commit"))
    if status == "partial":
        step(action("intervene",source,put))
        ready = False
        for _ in range(3):
            result = step(action("wait"))
            ready |= any(e.get("kind")=="feed_pulse" and e.get("status")=="ready"
                         for e in result["observation"]["delayed_events"])
        if not ready:
            raise RuntimeError("R5_PUBLIC_B_SECOND_FEED_NOT_CONFIRMED")
    step(action("intervene",found_relay,put))
    sink = None
    for _ in range(3):
        result = step(action("wait"))
        for event in result["observation"]["delayed_events"]:
            if event.get("kind") == "dependence_pulse":
                sink = event["entity"]
    if sink is None or len({source,found_relay,sink}) != 3:
        return step(action("commit"))
    step(action("intervene",sink,put))
    for _ in range(3):
        step(action("wait"))
    return step(action("commit"))


def fixed_open_loop(reset, step):
    labels = sorted(e["id"] for e in reset["entities"])
    value = reset["entities"][0]["legal_values"][0]
    for name in labels[:3]:
        step(action("intervene",name,value))
    for _ in range(3):
        step(action("wait"))
    return step(action("commit"))


def run_public_policy(family,seed,policy,episode):
    world = R5CausalWorld(family,episode,seed)
    first = json.loads(canonical(world.reset()))
    # An agent is given the copied observation and a public-step callable.
    def public_step(chosen):
        return json.loads(canonical(world.step(chosen)))
    result = (public_causal_oracle(first,public_step)
              if policy=="oracle" else fixed_open_loop(first,public_step))
    rec = world.public_trace_receipt()
    if not rec["done"] or rec["steps"] > MAX_INTERACTIONS or rec["scientific_first_use"]:
        raise AssertionError("R5_INVALID_PUBLIC_EPISODE")
    return {"reward":result["reward"], "steps":rec["steps"],
            "sha256":rec["trace_head_sha256"],"scientific_first_use":False}


def public_calibration(n=120):
    result = {}
    for fi,family in enumerate(PUBLIC_FAMILIES):
        counters = {}
        for p in ("oracle","fixed"):
            xs = [run_public_policy(family,530000+fi*100000+i,p,
                                    f"DEV-R5-{p}-{fi}-{i}") for i in range(n)]
            counters[p] = {"success":sum(x["reward"] for x in xs)/n,
                           "n":n, "mean_steps":sum(x["steps"] for x in xs)/n,
                           "rewards_sha256":hashlib.sha256(canonical([x["reward"] for x in xs])).hexdigest(),
                           "public_trace_heads_sha256":hashlib.sha256(canonical([x["sha256"] for x in xs])).hexdigest()}
        result[family] = counters
    return result
