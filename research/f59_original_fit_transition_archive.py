"""F59 inert canonical log for *delivered* original public FIT transitions.

No Acrobot import, simulator, IO or source/first-use acceptance. Report hashes
prove only self consistency unless separately witnessed by original owner.
Frozen protocol: 730721b5dc39c713b4af12b58f694e8823e2b9c5.
"""
import hashlib
import json
import math
import re

SCHEMA = "forge.eureka.f59.public-fit-transition-archive.dev.v1"
PROTOCOL = "730721b5dc39c713b4af12b58f694e8823e2b9c5"
F51_BLOB = "d3114ac66589e6b9f623318da721449090cfd54a"
F56_BEHAVIOR_BLOB = "00a6901daa1b479e96d923bf46daa5a1f1be45b4"
ORIGINAL_COMMIT = "365080941ea3a815ac09e57a7d4ee263a142651d"
ORIGINAL_BLOB = "28c440af281858c30e95fb6023f19923065d64fe"
FIT_ROOTS = (21011, 21017, 21019, 21023, 21029, 21031)
EPISODES_PER_ROOT = 8
MAX_PER_EPISODE = 500
MAX_ROWS = len(FIT_ROOTS) * EPISODES_PER_ROOT * MAX_PER_EPISODE
MAX_ARCHIVE_BYTES = 18_000_000
GENESIS = hashlib.sha256(b"forge.f59.original-public-fit-log.dev.v1").hexdigest()
DIGEST = re.compile(r"[a-f0-9]{64}\Z")
# Immutable values independently read from original source-backed F51 artifact
# #13822517528, canonical report b51b8921d3abc6618f44f172eb3eea3b50c96ec98c4d88aa5012698059dbf0ac.
F51_EXPECTED_RECORDS = 8974
F51_EXPECTED_ACTION_COUNTS = (3604, 1824, 3546)
F51_EXPECTED_TRAINING_SHA256 = "63d31930006ec2f465e4becd989c1a0b922e15a0842ef991fe424074d436a31a"
F51_EXPECTED_EPISODES_SHA256 = "4616a94182e962d70171d0fe80604a83042343c3797456b0494e7dbc1983b5d3"
F51_VERIFIED_REPORT_SHA256 = "b51b8921d3abc6618f44f172eb3eea3b50c96ec98c4d88aa5012698059dbf0ac"


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      allow_nan=False, ensure_ascii=True).encode("utf-8")


def sha(obj):
    return hashlib.sha256(canonical(obj)).hexdigest()


def valid_obs(obs):
    """Public Acrobot cos/sin pairs and bounded angular velocity, not latent state."""
    if type(obs) not in (list, tuple) or len(obs) != 6:
        raise ValueError("F59_PUBLIC_STATE_DIMENSION")
    if any(type(v) not in (int, float) for v in obs):
        raise ValueError("F59_PUBLIC_STATE_NONNUMERIC")
    v = [float(x) for x in obs]
    if not all(math.isfinite(x) for x in v):
        raise ValueError("F59_PUBLIC_STATE_NONFINITE")
    if (any(abs(x) > 1.0001 for x in v[:4])
            or abs(v[0]*v[0]+v[1]*v[1]-1.) > 1e-4
            or abs(v[2]*v[2]+v[3]*v[3]-1.) > 1e-4
            or abs(v[4]) > 4*math.pi + 1e-5
            or abs(v[5]) > 9*math.pi + 1e-5):
        raise ValueError("F59_NONPHYSICAL_PUBLIC_OBSERVATION")
    return v


def behavior_probs(obs):
    """Original F51 known logger; same formula as archived F56 behavior_probs."""
    s = valid_obs(obs)
    energy = 2 if s[5] >= 0. else 0
    probs = [.2, .2, .2]
    if abs(s[5]) < .2:
        probs[energy] += .36
        probs[1] += .04
    else:
        probs[energy] += .4
    if (abs(sum(probs)-1.) > 1e-12 or min(probs) < .2-1e-12
            or max(probs) > .6+1e-12):
        raise ValueError("F59_BEHAVIOR_PROBABILITY_DRIFT")
    return probs


class FITEvidenceArchive:
    """An append-only *in-memory* receipt of externally supplied completed events."""
    def __init__(self):
        self.records = []
        self.episodes = []
        self.active = None
        self.head = GENESIS

    def open_episode(self, root, episode, episode_seed):
        n = len(self.episodes)
        if self.active is not None or n >= len(FIT_ROOTS)*EPISODES_PER_ROOT:
            raise ValueError("F59_UNFINISHED_OR_EXTRA_EPISODE")
        expected_root = FIT_ROOTS[n // EPISODES_PER_ROOT]
        expected_episode = n % EPISODES_PER_ROOT
        if (type(root) is not int or type(episode) is not int
                or type(episode_seed) is not int
                or (root, episode, episode_seed) !=
                (expected_root, expected_episode, expected_root*100+expected_episode)):
            raise ValueError("F59_NOT_ORDERED_ORIGINAL_FIT_EPISODE")
        self.active = {"root": root, "episode": episode,
                       "episode_seed": episode_seed,
                       "start": len(self.records), "steps": 0, "last_next": None}

    def append(self, observation, action, reward, next_observation,
               terminated, truncated):
        active = self.active
        if active is None:
            raise ValueError("F59_NO_OPEN_EXPERIENCE")
        if active["steps"] >= MAX_PER_EPISODE or len(self.records) >= MAX_ROWS:
            raise ValueError("F59_EPISODE_OR_GLOBAL_BUDGET_EXCEEDED")
        before, after = valid_obs(observation), valid_obs(next_observation)
        if active["last_next"] is not None and before != active["last_next"]:
            raise ValueError("F59_DISCONTINUOUS_OBSERVED_TRAJECTORY")
        if type(action) is not int or action not in (0, 1, 2):
            raise ValueError("F59_ACTION_NOT_SELECTED_PUBLIC_TORQUE")
        if type(reward) not in (int, float) or not math.isfinite(reward):
            raise ValueError("F59_REWARD_NONFINITE")
        if type(terminated) is not bool or type(truncated) is not bool:
            raise ValueError("F59_NOT_EXPLICIT_TERMINAL_FLAGS")
        # Farama Acrobot v1.2.3 returns 0 precisely on physical success,
        # and -1 otherwise. TimeLimit can set truncated *also* true at t=500.
        if float(reward) != (0.0 if terminated else -1.0):
            raise ValueError("F59_REWARD_OR_TERMINATION_DISAGREES_WITH_ACROBOT")
        if terminated and truncated and active["steps"] + 1 != MAX_PER_EPISODE:
            raise ValueError("F59_PREMATURE_DUAL_TERMINAL_FLAGS")
        if active["steps"] + 1 == MAX_PER_EPISODE and not (terminated or truncated):
            raise ValueError("F59_MISSING_TIMELIMIT_TERMINAL")
        # Truncation under original TimeLimit is exactly 500 actions.
        if truncated and active["steps"] + 1 != MAX_PER_EPISODE:
            raise ValueError("F59_PREMATURE_TIMELIMIT_TRUNCATION")
        probs = behavior_probs(before)
        packet = {"seq": len(self.records), "root": active["root"],
                  "episode": active["episode"], "episode_seed": active["episode_seed"],
                  "t": active["steps"], "obs": before, "action": action,
                  "behavior_probability": probs[action], "reward": float(reward),
                  "next_obs": after, "terminated": terminated, "truncated": truncated,
                  "prev_sha256": self.head}
        packet["event_sha256"] = sha(packet)
        self.records.append(packet)
        self.head = packet["event_sha256"]
        active["steps"] += 1
        active["last_next"] = after
        if terminated or truncated:
            sub = self.records[active["start"]:]
            self.episodes.append({"root": active["root"], "episode": active["episode"],
                                  "episode_seed": active["episode_seed"],
                                  "start": active["start"], "steps": active["steps"],
                                  "trace_sha256": sha(sub)})
            self.active = None
        return packet["event_sha256"]

    def _payload(self):
        return {"schema": SCHEMA, "protocol": PROTOCOL,
                "source": {"original_commit": ORIGINAL_COMMIT,
                           "original_blob": ORIGINAL_BLOB,
                           "f51_source_blob": F51_BLOB,
                           "f56_behavior_blob": F56_BEHAVIOR_BLOB,
                           "mode": "book", "source_authenticated": False,
                           "scientific_accepted": False,
                           "original_first_use_permitted": False},
                "episode_slots": len(FIT_ROOTS)*EPISODES_PER_ROOT,
                "records": self.records, "episodes": self.episodes,
                "active": self.active, "head": self.head,
                "rows": len(self.records), "complete":
                self.active is None and len(self.episodes) ==
                len(FIT_ROOTS)*EPISODES_PER_ROOT}

    def snapshot(self):
        raw = canonical(self._payload())
        if len(raw) > MAX_ARCHIVE_BYTES:
            raise ValueError("F59_BOUNDED_ARCHIVE_BYTES_EXCEEDED")
        return raw, hashlib.sha256(raw).hexdigest()

    def seal_complete(self):
        if self.active is not None or len(self.episodes) != len(FIT_ROOTS)*EPISODES_PER_ROOT:
            raise ValueError("F59_ARCHIVE_MISSING_OR_UNFINISHED_EPISODES")
        return self.snapshot()

    @classmethod
    def restore(cls, raw, expected_external_sha256, minimum_rows):
        if (type(raw) is not bytes or len(raw) > MAX_ARCHIVE_BYTES
                or type(expected_external_sha256) is not str
                or not DIGEST.fullmatch(expected_external_sha256)
                or hashlib.sha256(raw).hexdigest() != expected_external_sha256
                or type(minimum_rows) is not int or not 0 <= minimum_rows <= MAX_ROWS):
            raise ValueError("F59_EXTERNAL_DIGEST_OR_FLOOR_INVALID")
        def unique(pairs):
            obj = {}
            for key, value in pairs:
                if key in obj:
                    raise ValueError("F59_DUPLICATE_JSON_KEY")
                obj[key] = value
            return obj
        try:
            obj = json.loads(raw, object_pairs_hook=unique,
                             parse_constant=lambda _: (_ for _ in ()).throw(
                                 ValueError("F59_NONFINITE_JSON")))
        except (UnicodeError, ValueError) as exc:
            raise ValueError("F59_MALFORMED_ARCHIVE") from exc
        if (type(obj) is not dict or set(obj) !=
                {"schema", "protocol", "source", "episode_slots", "records",
                 "episodes", "active", "head", "rows", "complete"}
                or obj["schema"] != SCHEMA or obj["protocol"] != PROTOCOL
                or obj["source"] != cls()._payload()["source"]
                or obj["episode_slots"] != len(FIT_ROOTS)*EPISODES_PER_ROOT
                or canonical(obj) != raw
                or type(obj["records"]) is not list
                or type(obj["rows"]) is not int
                or obj["rows"] < minimum_rows
                or obj["rows"] != len(obj["records"]) or obj["rows"] > MAX_ROWS):
            raise ValueError("F59_ARCHIVE_SCHEMA_OR_CUSTODY_INVALID")
        scratch = cls()
        for event in obj["records"]:
            if (type(event) is not dict or set(event) !=
                    {"seq", "root", "episode", "episode_seed", "t", "obs",
                     "action", "behavior_probability", "reward", "next_obs",
                     "terminated", "truncated", "prev_sha256", "event_sha256"}):
                raise ValueError("F59_EVENT_SCHEMA_INVALID")
            if scratch.active is None:
                scratch.open_episode(event["root"], event["episode"],
                                     event["episode_seed"])
            predicted = scratch.append(event["obs"], event["action"], event["reward"],
                                       event["next_obs"], event["terminated"],
                                       event["truncated"])
            if (predicted != event["event_sha256"] or
                    scratch.records[-1] != event):
                raise ValueError("F59_EVENT_OR_PROPENSITY_FORGED")
        if obj["active"] is not None and scratch.active is None:
            # The only otherwise unrepresented case is a just-opened empty episode.
            a = obj["active"]
            if (type(a) is not dict or set(a) !=
                    {"root", "episode", "episode_seed", "start", "steps", "last_next"}
                    or a["steps"] != 0 or a["last_next"] is not None
                    or a["start"] != len(scratch.records)):
                raise ValueError("F59_UNMATCHED_EMPTY_EPISODE")
            scratch.open_episode(a["root"], a["episode"], a["episode_seed"])
        if scratch.snapshot()[0] != raw:
            raise ValueError("F59_EPISODE_SEQUENCE_CHAIN_OR_RAW_DRIFT")
        return scratch

    def f51_legacy_digests(self):
        """Reconstruct *original* F51 record/episode hashes; no source execution.

        F59's own event/episode hash chains are deliberately a DIFFERENT
        schema from F51's historical training SHA. Never conflate them.
        """
        if self.active is not None or len(self.episodes) != len(FIT_ROOTS)*EPISODES_PER_ROOT:
            raise ValueError("F59_F51_ARCHIVE_NOT_FULLY_SEALED")
        rows = []
        summaries = []
        counts = [0, 0, 0]
        offset = 0
        for slot, ep in enumerate(self.episodes):
            root = FIT_ROOTS[slot // EPISODES_PER_ROOT]
            index = slot % EPISODES_PER_ROOT
            if (ep["root"] != root or ep["episode"] != index or
                    ep["start"] != offset or ep["steps"] < 1 or
                    ep["steps"] > MAX_PER_EPISODE):
                raise ValueError("F59_F51_EPISODE_ORDER_OR_LENGTH_DRIFT")
            events = self.records[offset:offset+ep["steps"]]
            if len(events) != ep["steps"] or not (events[-1]["terminated"] or events[-1]["truncated"]):
                raise ValueError("F59_F51_TERMINAL_OR_SLICE_DRIFT")
            f51_rows = []
            for event in events:
                counts[event["action"]] += 1
                f51_rows.append([event["obs"], event["action"], event["reward"],
                                 event["next_obs"], event["terminated"], event["truncated"]])
            rows.extend(f51_rows)
            summaries.append({"seed": root, "episode": index,
                              "steps": ep["steps"],
                              "terminated": events[-1]["terminated"],
                              "trace_sha256": sha(f51_rows)})
            offset += ep["steps"]
        if offset != len(self.records) or sum(counts) != offset:
            raise ValueError("F59_F51_EPISODE_TOTAL_DRIFT")
        return {"train_transition_count": offset,
                "train_action_counts": counts,
                "train_episode_count": len(summaries),
                "training_sha256": sha(rows),
                "training_episodes_sha256": sha(summaries)}

    def verify_historical_f51(self):
        """Fail closed unless delivered complete raw rows match ORIGINAL F51.

        Source authentication, original first-use and scientific acceptance
        remain false even after a digest match: those are separate authorities.
        """
        observed = self.f51_legacy_digests()
        if (observed["train_transition_count"] != F51_EXPECTED_RECORDS or
            tuple(observed["train_action_counts"]) != F51_EXPECTED_ACTION_COUNTS or
            observed["train_episode_count"] != len(FIT_ROOTS)*EPISODES_PER_ROOT or
            observed["training_sha256"] != F51_EXPECTED_TRAINING_SHA256 or
            observed["training_episodes_sha256"] != F51_EXPECTED_EPISODES_SHA256):
            raise ValueError("F59_F51_HISTORICAL_TRANSCRIPT_MISMATCH")
        return {"historical_f51_training_hashes_match": True,
                "f51_original_report_sha256": F51_VERIFIED_REPORT_SHA256,
                "source_authenticated": False,
                "original_first_use_permitted": False,
                "scientific_accepted": False,
                **observed}
