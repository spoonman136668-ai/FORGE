"""NR-M2G: source-only online action-conditioned structural public-effect cells.

Learns independent scalar copy/constant-overwrite rules across all 441
public image components, original heading and original mission. No original
environment or native model is executed; the supplied admission validator
is the exact pinned NR-M2E public-source interface in qualification.
Artificial invariant effects can transfer to unseen public states. This is a
conventional structured hypothesis, NOT a scientifically unique mechanism.
"""
import hashlib
import json

SCHEMA = "nr-m2g.source-only-public-structural-effect.v1"
MAX_PER_ACTION = 128
MAX_TOTAL = 896
MAX_SNAPSHOT_BYTES = 5000000
MIN_SUPPORT = 4
COMPONENTS = 443

def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def components(public):
    return [value for row in public["image"] for pixel in row for value in pixel] + [public["direction"], public["mission"]]

def unpack(values):
    if len(values) != COMPONENTS:
        raise ValueError("PUBLIC_COMPONENT_WIDTH")
    image = [[values[3 * (7 * y + x):3 * (7 * y + x) + 3] for x in range(7)] for y in range(7)]
    return {"image": image, "direction": values[441], "mission": values[442]}

class StructuralEffectCells:
    def __init__(self, admission):
        self.admission = admission
        self.rows = [[] for _ in range(7)]
        self.pending = None
        self.current = None
        self.episodes = 0
        self.events = 0
        self.evictions = 0
        self._cache = {}

    def begin(self, public):
        if self.pending is not None:
            raise ValueError("PENDING_ACTION_AT_RESET")
        self.current = self.admission(public)
        self.episodes += 1

    def select(self, before, action):
        observed = self.admission(before)
        if (self.current is None or self.pending is not None or
            canonical(observed) != canonical(self.current)):
            raise ValueError("SELECTED_SOURCE_ORDER")
        if type(action) is not int or action not in range(7):
            raise ValueError("INVALID_ORIGINAL_ACTION")
        self.pending = (observed, action)

    def feedback(self, before, action, returned):
        observed = self.admission(before)
        after = self.admission(returned)
        if (type(action) is not int or self.pending is None or
            self.pending[1] != action or
            canonical(self.pending[0]) != canonical(observed) or
            canonical(self.current) != canonical(observed)):
            raise ValueError("UNMATCHED_SELECTED_FEEDBACK")
        if observed["mission"] != after["mission"]:
            raise ValueError("SOURCE_MISSION_DRIFT")
        if self.events == MAX_TOTAL:
            raise ValueError("TOTAL_SELECTED_EVENT_CAP")
        row = self.rows[action]
        if len(row) == MAX_PER_ACTION:
            del row[0]
            self.evictions += 1
        row.append([observed, after])
        self.events += 1
        self.current = after
        self.pending = None
        self._cache.pop(action, None)

    def _rules(self, action):
        if action in self._cache:
            return self._cache[action]
        row = self.rows[action]
        if len(row) < MIN_SUPPORT:
            self._cache[action] = None
            return None
        observed = [(components(before), components(after)) for before, after in row]
        rules = []
        for i in range(COMPONENTS):
            before_values = [before[i] for before, _ in observed]
            after_values = [after[i] for _, after in observed]
            # All evidence is copy: extrapolate if there is variable source
            # support; otherwise copy ONLY the already-supported input value.
            if all(b == y for b, y in zip(before_values, after_values)):
                if len(set(before_values)) >= 2:
                    rules.append(("copy", None))
                else:
                    rules.append(("limited-copy", before_values[0]))
            # A constant post-effect independently supported by varied prior
            # input values. No hidden mission or world identifier.
            elif len(set(after_values)) == 1 and len(set(before_values)) >= 2:
                rules.append(("constant", after_values[0]))
            else:
                rules.append(("abstain", None))
        self._cache[action] = rules
        return rules

    def predict(self, before, action):
        observed = self.admission(before)
        if type(action) is not int or action not in range(7):
            raise ValueError("INVALID_ORIGINAL_ACTION")
        rules = self._rules(action)
        if rules is None:
            return None, {"supported": False, "reason": "INSUFFICIENT_SELECTED_EVIDENCE"}
        source = components(observed)
        result = []
        for value, (op, bound) in zip(source, rules):
            if op == "copy":
                result.append(value)
            elif op == "limited-copy" and value == bound:
                result.append(value)
            elif op == "constant":
                result.append(bound)
            else:
                return None, {"supported": False, "reason": "UNSUPPORTED_OR_CONTRADICTORY_COMPONENT"}
        after = self.admission(unpack(result))
        return after, {"supported": True, "no_effect": canonical(after) == canonical(observed),
                       "selected_support": len(self.rows[action])}

    def forecast(self, before, actions):
        if type(actions) not in (list, tuple) or not 1 <= len(actions) <= 5:
            raise ValueError("INVALID_COMPOSITION")
        state = self.admission(before)
        for action in actions:
            state, evidence = self.predict(state, action)
            if not evidence["supported"]:
                return None, evidence
        return state, {"supported": True, "steps": len(actions)}

    def checkpoint(self):
        if self.pending is not None:
            raise ValueError("PENDING_CHECKPOINT")
        body = {"schema": SCHEMA, "rows": self.rows, "current": self.current,
                "episodes": self.episodes, "events": self.events, "evictions": self.evictions}
        raw = canonical(body)
        if len(raw) > MAX_SNAPSHOT_BYTES:
            raise ValueError("SNAPSHOT_CAP")
        return raw

    @classmethod
    def restore(cls, admission, raw, trusted_sha):
        if (type(raw) is not bytes or not raw or len(raw) > MAX_SNAPSHOT_BYTES or
            type(trusted_sha) is not str or sha(raw) != trusted_sha):
            raise ValueError("UNTRUSTED_CHECKPOINT")
        try:
            body = json.loads(raw)
            if (canonical(body) != raw or
                set(body) != {"schema", "rows", "current", "episodes", "events", "evictions"} or
                body["schema"] != SCHEMA or
                type(body["rows"]) is not list or len(body["rows"]) != 7):
                raise ValueError("BAD_SNAPSHOT_SCHEMA")
            state = cls(admission)
            for field in ("episodes", "events", "evictions"):
                if type(body[field]) is not int or body[field] < 0:
                    raise ValueError("BAD_COUNTER")
                setattr(state, field, body[field])
            if state.events > MAX_TOTAL or state.evictions > state.events:
                raise ValueError("BAD_SELECTED_COUNTER")
            state.current = admission(body["current"]) if body["current"] is not None else None
            for action, pairs in enumerate(body["rows"]):
                if type(pairs) is not list or len(pairs) > MAX_PER_ACTION:
                    raise ValueError("BAD_ACTION_WINDOW")
                for pair in pairs:
                    if type(pair) is not list or len(pair) != 2:
                        raise ValueError("BAD_SELECTED_PAIR")
                    before, after = admission(pair[0]), admission(pair[1])
                    if before["mission"] != after["mission"]:
                        raise ValueError("MISSION_DRIFT")
                    state.rows[action].append([before, after])
            if (sum(map(len, state.rows)) + state.evictions != state.events or
                (state.episodes == 0 and state.events != 0) or
                (state.events and state.current is None) or
                state.checkpoint() != raw):
                raise ValueError("SOURCE_CUSTODY_DRIFT")
            return state
        except (ValueError, KeyError, TypeError, OverflowError, UnicodeError) as exc:
            raise ValueError("INVALID_SOURCE_RESTORE") from exc
