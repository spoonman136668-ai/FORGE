"""NR-M2H learned public precondition effects -- source-only engineering.

No hardcoded public cue indices, door/key rules, original-world steps,
privileged world state or test-fixture functions. This bounded exact
selected-feedback state is NOT an accepted native scientific model.
"""
import hashlib
import json

SCHEMA = "nr-m2h.source-only.learned-public-predicate.v1"
N_ACTIONS = 7
N_FIELDS = 149
MAX_EVENTS = 896
MAX_PER_ACTION = 128
MAX_CHECKPOINT = 5000000
MIN_SUPPORT = 4

def canonical(v):
    return json.dumps(v, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()

def feature_vector(public):
    return [value for row in public["image"] for pixel in row for value in pixel] + [
        public["direction"], public["mission"]]

def public_frame(values):
    if type(values) is not list or len(values) != N_FIELDS:
        raise ValueError("PUBLIC_COMPONENT_COUNT")
    return {
        "image": [[values[(row*7+col)*3:(row*7+col)*3+3]
                   for col in range(7)] for row in range(7)],
        "direction": values[147], "mission": values[148],
    }

def leaf_rule(pairs, target):
    before = [b[target] for b, _ in pairs]
    after = [y[target] for _, y in pairs]
    if all(x == y for x, y in zip(before, after)):
        return ("copy", None) if len(set(before)) > 1 else ("limited", before[0])
    if len(set(after)) == 1:
        # A single previously seen input is allowed ONLY at that input.
        if len(set(before)) == 1:
            return ("limited-write", (before[0], after[0]))
        return ("write", after[0])
    return None

class LearnedPublicPreconditions:
    def __init__(self, admission):
        self.admission = admission
        self.samples = [[] for _ in range(N_ACTIONS)]
        self.current = None
        self.pending = None
        self.events = 0
        self.evicted = 0
        self.episodes = 0
        self._cache = {}

    def begin(self, public):
        if self.pending is not None:
            raise ValueError("PENDING_SOURCE_ACTION")
        self.current = self.admission(public)
        self.episodes += 1

    def select(self, before, action):
        before = self.admission(before)
        if type(action) is not int or not 0 <= action < N_ACTIONS:
            raise ValueError("INVALID_SOURCE_ACTION")
        if self.current is None or self.pending is not None or canonical(self.current) != canonical(before):
            raise ValueError("NOT_NEXT_SELECTED_ACTION")
        self.pending = (before, action)

    def feedback(self, before, action, after):
        before, after = self.admission(before), self.admission(after)
        if (self.pending is None or type(action) is not int or
            self.pending[1] != action or canonical(self.pending[0]) != canonical(before) or
            self.current is None or canonical(self.current) != canonical(before)):
            raise ValueError("UNCOMMITTED_SELECTED_FEEDBACK")
        if before["mission"] != after["mission"]:
            raise ValueError("MISSION_CHANGED")
        if self.events >= MAX_EVENTS:
            raise ValueError("TOTAL_SELECTED_SOURCE_BUDGET")
        if len(self.samples[action]) == MAX_PER_ACTION:
            self.samples[action].pop(0)
            self.evicted += 1
        self.samples[action].append([before, after])
        self.events += 1
        self.current = after
        self.pending = None
        self._cache.pop(action, None)

    def _compile(self, action):
        if action in self._cache:
            return self._cache[action]
        rows = self.samples[action]
        if len(rows) < MIN_SUPPORT:
            self._cache[action] = None
            return None
        pairs = [(feature_vector(b), feature_vector(y)) for b, y in rows]
        rules = []
        for target in range(N_FIELDS):
            unconditional = leaf_rule(pairs, target)
            # Conditional hypothesis only if action's target effect genuinely
            # depends on a public before-state predicate; no cue positions fixed.
            if unconditional is not None:
                rules.append(("plain", unconditional))
                continue
            selected = None
            for cue in range(N_FIELDS):
                values = set(b[cue] for b, _ in pairs)
                if len(values) != 2:
                    continue
                sorted_vals = sorted(values, key=lambda v: (type(v).__name__, str(v)))
                left = [pair for pair in pairs if pair[0][cue] == sorted_vals[0]]
                right = [pair for pair in pairs if pair[0][cue] == sorted_vals[1]]
                if len(left) < MIN_SUPPORT or len(right) < MIN_SUPPORT:
                    continue
                lrule = leaf_rule(left, target)
                rrule = leaf_rule(right, target)
                if lrule is None or rrule is None:
                    continue
                # Avoid making a split for a spurious difference of formatting:
                # changed/unchanged outcomes must be distinguishable by cue.
                if (any(b[target] != y[target] for b, y in left) ==
                    any(b[target] != y[target] for b, y in right)):
                    continue
                selected = ("split", cue, sorted_vals, lrule, rrule)
                break
            rules.append(selected if selected is not None else ("abstain", None))
        self._cache[action] = rules
        return rules

    @staticmethod
    def _apply(rule, x):
        typ, datum = rule
        if typ == "copy":
            return x, True
        if typ == "limited":
            return x, x == datum
        if typ == "write":
            return datum, True
        if typ == "limited-write":
            return datum[1], x == datum[0]
        return None, False

    def predict(self, public, action):
        public = self.admission(public)
        if type(action) is not int or not 0 <= action < N_ACTIONS:
            raise ValueError("INVALID_SOURCE_ACTION")
        rules = self._compile(action)
        if rules is None:
            return None, {"supported": False, "reason": "INSUFFICIENT_SELECTED_FEEDBACK"}
        before = feature_vector(public)
        result = []
        for index, rule in enumerate(rules):
            if rule[0] == "plain":
                leaf = rule[1]
            elif rule[0] == "split":
                _, cue, seen, left, right = rule
                if before[cue] not in seen:
                    return None, {"supported": False, "reason": "UNSEEN_PRECONDITION"}
                leaf = left if before[cue] == seen[0] else right
            else:
                return None, {"supported": False, "reason": "AMBIGUOUS_PUBLIC_EFFECT"}
            value, supported = self._apply(leaf, before[index])
            if not supported:
                return None, {"supported": False, "reason": "UNSUPPORTED_PUBLIC_BRANCH"}
            result.append(value)
        returned = self.admission(public_frame(result))
        return returned, {"supported": True,
                          "no_effect": canonical(returned) == canonical(public),
                          "selected_support": len(self.samples[action])}

    def forecast(self, public, actions):
        if type(actions) not in (list, tuple) or not 1 <= len(actions) <= 5:
            raise ValueError("FORECAST_HORIZON")
        state = self.admission(public)
        for action in actions:
            state, info = self.predict(state, action)
            if not info["supported"]:
                return None, info
        return state, {"supported": True, "steps": len(actions)}

    def checkpoint(self):
        if self.pending is not None:
            raise ValueError("UNRETURNED_CHECKPOINT")
        raw = canonical({"schema": SCHEMA, "samples": self.samples, "current": self.current,
                         "events": self.events, "evicted": self.evicted, "episodes": self.episodes})
        if len(raw) > MAX_CHECKPOINT:
            raise ValueError("CHECKPOINT_BUDGET")
        return raw

    @classmethod
    def restore(cls, admission, raw, trusted_sha):
        if (type(raw) is not bytes or not 0 < len(raw) <= MAX_CHECKPOINT or
            type(trusted_sha) is not str or hashlib.sha256(raw).hexdigest() != trusted_sha):
            raise ValueError("UNTRUSTED_CHECKPOINT")
        try:
            data = json.loads(raw)
            if (canonical(data) != raw or
                set(data) != {"schema", "samples", "current", "events", "evicted", "episodes"} or
                data["schema"] != SCHEMA or type(data["samples"]) is not list or
                len(data["samples"]) != N_ACTIONS):
                raise ValueError("CHECKPOINT_SCHEMA")
            for key in ("events", "evicted", "episodes"):
                if type(data[key]) is not int or data[key] < 0:
                    raise ValueError("CHECKPOINT_COUNTER")
            if (data["events"] > MAX_EVENTS or data["evicted"] > data["events"] or
                (data["events"] and (not data["episodes"] or data["current"] is None))):
                raise ValueError("CHECKPOINT_CUSTODY")
            model = cls(admission)
            model.events, model.evicted, model.episodes = data["events"], data["evicted"], data["episodes"]
            model.current = admission(data["current"]) if data["current"] is not None else None
            for action, events in enumerate(data["samples"]):
                if type(events) is not list or len(events) > MAX_PER_ACTION:
                    raise ValueError("BAD_ACTION_WINDOW")
                for item in events:
                    if type(item) is not list or len(item) != 2:
                        raise ValueError("BAD_SOURCE_EVENT")
                    before, after = admission(item[0]), admission(item[1])
                    if before["mission"] != after["mission"]:
                        raise ValueError("MISSION_DRIFT")
                    model.samples[action].append([before, after])
            if sum(map(len, model.samples)) + model.evicted != model.events:
                raise ValueError("EVENT_COUNT_MISMATCH")
            if model.checkpoint() != raw:
                raise ValueError("CHECKPOINT_NONCANONICAL")
            return model
        except (TypeError, ValueError, KeyError, OverflowError, UnicodeError) as exc:
            raise ValueError("CHECKPOINT_REJECTED") from exc
