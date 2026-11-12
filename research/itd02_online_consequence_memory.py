#!/usr/bin/env python3
"""Offline numerical action/consequence memory. No experiment, I/O or FSA grant.

Only consumes explicitly delivered public observation, executed action and
observed consequence. It does not step a world, generate counterfactuals,
train from future rewards or authenticate the provenance of its input stream.
"""
import hashlib
import json
import math
import re

SCHEMA = "forge.eureka.itd02.online-consequence-memory.dev.v1"
PROTOCOL_COMMIT = "38234f3158bc6dacfe2328ab0cdfb6d1fe1c5676"
PROTOCOL_BLOB = "fc415a6b81b1b94be427366e2af35ca5ef162461"
RIDGE = 0.1
MAX_SNAPSHOT_BYTES = 65536
START_DIGEST = "0" * 64
_HEX = re.compile(r"^[0-9a-f]{64}$")


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _hash(payload):
    return hashlib.sha256(payload).hexdigest()


def _finite(value, *, lower=None, upper=None):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError("ITD02_NONFINITE_NUMERICAL_INPUT")
    result = float(value)
    if (lower is not None and result < lower) or (upper is not None and result > upper):
        raise ValueError("ITD02_NUMERICAL_BUDGET_VIOLATION")
    return result


def _vector(raw, dim):
    if type(raw) not in (list, tuple) or len(raw) != dim:
        raise ValueError("ITD02_PUBLIC_VECTOR_DIMENSION_INVALID")
    return [1.0] + [_finite(x, lower=-1., upper=1.) for x in raw]


def _positive_definite(matrix):
    """Cholesky domain check for restored matrices; not proof of origin."""
    n = len(matrix)
    l = [[0.] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1):
            s = matrix[i][j] - sum(l[i][k] * l[j][k] for k in range(j))
            if i == j:
                if not math.isfinite(s) or s <= 1e-12:
                    raise ValueError("ITD02_NONPOSITIVE_NORMAL_MATRIX")
                l[i][j] = math.sqrt(s)
            else:
                l[i][j] = s / l[j][j]
        for j in range(i + 1, n):
            if abs(matrix[i][j] - matrix[j][i]) > 1e-9:
                raise ValueError("ITD02_ASYMMETRIC_NORMAL_MATRIX")


def _solve(matrix, target):
    """Deterministic Gaussian elimination; inputs are tiny SPD ridge matrices."""
    size = len(target)
    a = [list(matrix[i]) + [float(target[i])] for i in range(size)]
    for k in range(size):
        pivot = max(range(k, size), key=lambda i: (abs(a[i][k]), -i))
        if not math.isfinite(a[pivot][k]) or abs(a[pivot][k]) <= 1e-12:
            raise ValueError("ITD02_SINGULAR_NUMERICAL_MODEL")
        a[k], a[pivot] = a[pivot], a[k]
        divisor = a[k][k]
        for j in range(k, size + 1):
            a[k][j] /= divisor
        for i in range(size):
            if i != k:
                multiplier = a[i][k]
                for j in range(k, size + 1):
                    a[i][j] -= multiplier * a[k][j]
    answer = [a[i][size] for i in range(size)]
    if not all(math.isfinite(v) for v in answer):
        raise ValueError("ITD02_NONFINITE_NUMERICAL_SOLVE")
    return answer


def _unique_object(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise ValueError("ITD02_DUPLICATE_SNAPSHOT_JSON_KEY")
        out[key] = value
    return out


class OnlineConsequenceMemory:
    """Bounded context-conditioned, separately fitted online action response."""

    def __init__(self, public_dim=2, actions=3, max_events=10000):
        if (type(public_dim) is not int or not 2 <= public_dim <= 6 or
            type(actions) is not int or not 2 <= actions <= 6 or
            type(max_events) is not int or not 1 <= max_events <= 10000):
            raise ValueError("ITD02_FROZEN_CAPACITY_INVALID")
        self.public_dim = public_dim
        self.actions = actions
        self.max_events = max_events
        self.completed = 0
        self.counts = [0] * actions
        n = public_dim + 1
        self.grams = [
            [[RIDGE if i == j else 0. for j in range(n)] for i in range(n)]
            for _ in range(actions)
        ]
        self.sums = [[0.] * n for _ in range(actions)]
        self.event_digest = START_DIGEST

    def _action(self, action):
        if type(action) is not int or not 0 <= action < self.actions:
            raise ValueError("ITD02_UNOBSERVED_OR_INVALID_INTERVENTION")
        return action

    def predict(self, observation, action):
        p = _vector(observation, self.public_dim)
        k = self._action(action)
        theta = _solve(self.grams[k], self.sums[k])
        answer = sum(a * b for a, b in zip(p, theta))
        if not math.isfinite(answer):
            raise ValueError("ITD02_NONFINITE_PREDICTED_CONSEQUENCE")
        return answer

    def uncertainty(self, observation, action):
        p = _vector(observation, self.public_dim)
        k = self._action(action)
        direction = _solve(self.grams[k], p)
        variance = sum(a * b for a, b in zip(p, direction))
        if not math.isfinite(variance) or variance < -1e-9:
            raise ValueError("ITD02_INVALID_UNCERTAINTY")
        return math.sqrt(max(variance, 0.))

    def propose(self, observation, exploration_weight=0.):
        """Read-only advice. NO environment action or implicit observation."""
        _vector(observation, self.public_dim)
        weight = _finite(exploration_weight, lower=0., upper=5.)
        expected = [self.predict(observation, a) for a in range(self.actions)]
        scores = [v + weight * self.uncertainty(observation, a)
                  for a, v in enumerate(expected)]
        greedy = max(range(self.actions), key=lambda a: (expected[a], -a))
        selected = max(range(self.actions), key=lambda a: (scores[a], -a))
        return {"action": selected, "greedy_action": greedy,
                "information_seeking": selected != greedy,
                "predicted_consequence": expected[selected],
                "observed_events": self.completed,
                "can_dispatch_original": False, "scientific_accepted": False}

    def observe(self, event_seq, observation, action, consequence):
        """Update only a *supplied, already observed* real action consequence."""
        if type(event_seq) is not int or event_seq != self.completed:
            raise ValueError("ITD02_DUPLICATE_SKIPPED_OR_OUT_OF_ORDER_EVENT")
        if self.completed >= self.max_events:
            raise ValueError("ITD02_OBSERVATION_BUDGET_EXCEEDED")
        p = _vector(observation, self.public_dim)
        k = self._action(action)
        y = _finite(consequence, lower=-100., upper=100.)
        # All validation before the first state mutation.
        event = {"seq": event_seq, "obs": p[1:], "action": k,
                 "observed_consequence": y}
        next_digest = _hash(bytes.fromhex(self.event_digest) + _canonical(event))
        # Small, bounded input ensures finite matrix update; reject without mutation.
        new_gram = [[self.grams[k][i][j] + p[i] * p[j]
                     for j in range(len(p))] for i in range(len(p))]
        new_sum = [self.sums[k][i] + p[i] * y for i in range(len(p))]
        if not all(math.isfinite(v) for row in new_gram for v in row) or not all(
                math.isfinite(v) for v in new_sum):
            raise ValueError("ITD02_NUMERICAL_OBSERVATION_OVERFLOW")
        self.grams[k] = new_gram
        self.sums[k] = new_sum
        self.counts[k] += 1
        self.completed += 1
        self.event_digest = next_digest

    def checkpoint(self):
        """Contents and digest only. NOT a source-signed or FSA-trusted receipt."""
        body = {"schema": SCHEMA, "protocol_commit": PROTOCOL_COMMIT,
                "protocol_blob": PROTOCOL_BLOB, "ridge": RIDGE,
                "public_dim": self.public_dim, "actions": self.actions,
                "max_events": self.max_events, "completed": self.completed,
                "counts": self.counts, "grams": self.grams, "sums": self.sums,
                "event_digest": self.event_digest,
                "original_first_use_authorized": False,
                "scientific_accepted": False}
        payload = _canonical(body)
        if len(payload) > MAX_SNAPSHOT_BYTES:
            raise ValueError("ITD02_CHECKPOINT_SIZE_EXCEEDED")
        return payload, _hash(payload)

    @classmethod
    def restore(cls, payload, expected_sha256, minimum_completed=0):
        if (type(payload) is not bytes or len(payload) > MAX_SNAPSHOT_BYTES or
            not isinstance(expected_sha256, str) or not _HEX.fullmatch(expected_sha256) or
            _hash(payload) != expected_sha256):
            raise ValueError("ITD02_COLD_CHECKPOINT_HASH_MISMATCH")
        if type(minimum_completed) is not int or minimum_completed < 0:
            raise ValueError("ITD02_INVALID_EXTERNAL_MINIMUM")
        try:
            x = json.loads(payload.decode("utf-8"),
                           parse_constant=lambda _: (_ for _ in ()).throw(ValueError("ITD02_NONFINITE_JSON")),
                           object_pairs_hook=_unique_object)
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise ValueError("ITD02_INVALID_CHECKPOINT_JSON") from exc
        fields = {"schema", "protocol_commit", "protocol_blob", "ridge",
                  "public_dim", "actions", "max_events", "completed",
                  "counts", "grams", "sums", "event_digest",
                  "original_first_use_authorized", "scientific_accepted"}
        if (type(x) is not dict or set(x) != fields or
            x["schema"] != SCHEMA or x["protocol_commit"] != PROTOCOL_COMMIT or
            x["protocol_blob"] != PROTOCOL_BLOB or type(x["ridge"]) not in (int, float) or
            x["ridge"] != RIDGE or
            x["original_first_use_authorized"] is not False or
            x["scientific_accepted"] is not False or _canonical(x) != payload):
            raise ValueError("ITD02_COLD_SCHEMA_OR_PROTOCOL_DRIFT")
        obj = cls(x["public_dim"], x["actions"], x["max_events"])
        n = x["completed"]
        if (type(n) is not int or not minimum_completed <= n <= obj.max_events or
            type(x["counts"]) is not list or len(x["counts"]) != obj.actions or
            any(type(c) is not int or c < 0 for c in x["counts"]) or
            sum(x["counts"]) != n or
            type(x["event_digest"]) is not str or
            not _HEX.fullmatch(x["event_digest"]) or
            (n == 0 and x["event_digest"] != START_DIGEST) or
            (n > 0 and x["event_digest"] == START_DIGEST)):
            raise ValueError("ITD02_COLD_HISTORY_INCONSISTENT")
        dim = obj.public_dim + 1
        for name in ("grams", "sums"):
            items = x[name]
            if type(items) is not list or len(items) != obj.actions:
                raise ValueError("ITD02_COLD_NUMERICAL_SHAPE_INVALID")
            for block in items:
                if type(block) is not list or len(block) != dim:
                    raise ValueError("ITD02_COLD_NUMERICAL_SHAPE_INVALID")
                for row in (block if name == "grams" else [block]):
                    if (type(row) is not list or len(row) != dim or
                        any(type(v) not in (float, int) or not math.isfinite(v)
                            for v in row)):
                        raise ValueError("ITD02_COLD_NUMERICAL_SHAPE_INVALID")
        for matrix in x["grams"]:
            _positive_definite(matrix)
        obj.completed = n
        obj.counts = list(x["counts"])
        obj.grams = x["grams"]
        obj.sums = x["sums"]
        obj.event_digest = x["event_digest"]
        return obj
