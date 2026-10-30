"""NR-M2D: lossless source-original PUBLIC observation + selected-action custody.

THIS IS TRANSPORT ONLY, not a seven-action native causal learner. Every
observation here is externally supplied; the code never steps a source world.
Original MiniGrid public range validation is the *unchanged, source-pinned*
Yggdrasil R10 _image_lists function.
"""
from hashlib import sha256
import json
from pinned_original_r10 import (
    _image_lists, canonical, digest, ACTION_NAMES, MISSION,
    UPSTREAM_MINIGRID_COMMIT,
)

SCHEMA="forge.nr-m2d.original-public-source-only-boundary.v1"
R10_GIT_BLOB="3917d36ce9f86a2c1b998a0a2f93fb27674a9205"
MG19_GIT_BLOB="3db67b40d8d59fdfb41f89185b65d2f16e1d8aab"
MAX_EVENTS=4096
MAX_LEDGER=64
MAX_BYTES=250000
LEGACY=(MISSION,"get to the green goal square")

def admitted(mission):
    """Exact source-pinned MG19 admitted() contract; never infer a mission."""
    if type(mission) is not str:
        return False
    if mission in LEGACY:
        return True
    if not mission.startswith("pick up the ") or len(mission)>96:
        return False
    words=mission[len("pick up the "):].split(" ")
    return 2<=len(words)<=4 and all(
        word and all("a"<=c<="z" for c in word) for word in words
    )

def original_frame(frame):
    if type(frame) is not dict or set(frame)!={"image","direction","mission"}:
        raise ValueError("NRM2D_UNTRUSTED_OR_PRIVILEGED_SOURCE_FRAME")
    if type(frame["direction"]) is not int or frame["direction"] not in range(4):
        raise ValueError("NRM2D_UNTRUSTED_PUBLIC_DIRECTION")
    if not admitted(frame["mission"]):
        raise ValueError("NRM2D_UNADMITTED_ORIGINAL_MISSION")
    public={"image":_image_lists(frame["image"]),
            "direction":frame["direction"],"mission":frame["mission"]}
    if len(canonical(public))>4096:
        raise ValueError("NRM2D_UNBOUNDED_PUBLIC_FRAME")
    return public

def original_fingerprint(frame):
    return digest(original_frame(frame))

def original_action(selected):
    if type(selected) is not int or selected not in range(len(ACTION_NAMES)):
        raise ValueError("NRM2D_UNSUPPORTED_SOURCE_ACTION")
    return selected

def forbid_8bit_compatibility(frame, selected):
    # For every admitted full public frame, a conversion that discards the
    # remaining image or action identity is NOT an authorized R7 API.
    original_frame(frame)
    original_action(selected)
    raise ValueError("NRM2D_NO_LOSSLESS_EIGHT_BIT_THREE_ACTION_CODEC")

class SelectedPublicBoundary:
    def __init__(self):
        self.current=None
        self.pending=None
        self.events=0
        self.episodes=0
        self.ledger=[]

    def begin_episode(self, public):
        if self.pending is not None:
            raise ValueError("NRM2D_RESET_WITH_UNRETURNED_SOURCE_ACTION")
        self.current=original_frame(public)
        self.pending=None
        self.events=0
        self.episodes+=1
        self.ledger=[]

    def commit(self, public, selected):
        if self.current is None or self.pending is not None:
            raise ValueError("NRM2D_NO_SOURCE_SELECTION_OR_PENDING_ACTION")
        if self.events>=MAX_EVENTS:
            raise ValueError("NRM2D_SOURCE_ACTION_CAP")
        before=original_frame(public)
        if before!=self.current:
            raise ValueError("NRM2D_WRONG_SOURCE_BEFORE")
        action=original_action(selected)
        self.pending={"action":action,"before_sha256":digest(before)}
        return action

    def feedback(self,public_before,selected,public_after):
        before=original_frame(public_before)
        after=original_frame(public_after)
        action=original_action(selected)
        if (self.current is None or self.pending is None or
            before!=self.current or
            self.pending!={"action":action,"before_sha256":digest(before)}):
            raise ValueError("NRM2D_UNMATCHED_OR_DUPLICATE_SELECTED_FEEDBACK")
        if before["mission"]!=after["mission"]:
            raise ValueError("NRM2D_SOURCE_MISSION_DRIFT")
        # No hidden reward, goal, pose, grid or unchosen action enters this
        # ledger. It is only a single actually returned PUBLIC after frame.
        record={"ordinal":self.events+1,"selected":action,
                "before_public_sha256":digest(before),
                "after_public_sha256":digest(after)}
        self.current=after
        self.pending=None
        self.events+=1
        self.ledger=(self.ledger+[record])[-MAX_LEDGER:]
        return dict(record)

    def checkpoint(self):
        if self.pending is not None:
            raise ValueError("NRM2D_CANNOT_FREEZE_PENDING_SOURCE_ACTION")
        state={"schema":SCHEMA,"r10_git_blob":R10_GIT_BLOB,
               "mg19_git_blob":MG19_GIT_BLOB,
               "upstream_public_source":UPSTREAM_MINIGRID_COMMIT,
               "episodes":self.episodes,"events":self.events,
               "current":self.current,"pending":None,"ledger":self.ledger}
        raw=canonical({"state":state,"sha256":sha256(canonical(state)).hexdigest()})
        if len(raw)>MAX_BYTES:
            raise ValueError("NRM2D_SNAPSHOT_SIZE")
        return raw

    @classmethod
    def restore(cls,raw,trusted_sha):
        if (type(raw) is not bytes or not 0<len(raw)<=MAX_BYTES or
            type(trusted_sha) is not str or sha256(raw).hexdigest()!=trusted_sha):
            raise ValueError("NRM2D_UNTRUSTED_SNAPSHOT")
        try:
            env=json.loads(raw)
            if type(env) is not dict or set(env)!={"state","sha256"} or raw!=canonical(env):
                raise ValueError("NRM2D_SNAPSHOT_ENVELOPE")
            st=env["state"]
            if (type(st) is not dict or
                set(st)!={"schema","r10_git_blob","mg19_git_blob",
                          "upstream_public_source","episodes","events",
                          "current","pending","ledger"} or
                st["schema"]!=SCHEMA or st["r10_git_blob"]!=R10_GIT_BLOB or
                st["mg19_git_blob"]!=MG19_GIT_BLOB or
                st["upstream_public_source"]!=UPSTREAM_MINIGRID_COMMIT or
                sha256(canonical(st)).hexdigest()!=env["sha256"]):
                raise ValueError("NRM2D_SOURCE_CUSTODY_INVALID")
            if (type(st["episodes"]) is not int or type(st["events"]) is not int or
                not 0<=st["events"]<=MAX_EVENTS or
                not 0<=st["episodes"]<=MAX_EVENTS or
                st["pending"] is not None or
                type(st["ledger"]) is not list or
                len(st["ledger"])>min(st["events"],MAX_LEDGER)):
                raise ValueError("NRM2D_INVALID_SOURCE_COUNTS")
            current=st["current"]
            if (current is None)!=(st["episodes"]==0):
                raise ValueError("NRM2D_NO_PUBLIC_SOURCE_SESSION")
            if current is not None and original_frame(current)!=current:
                raise ValueError("NRM2D_NONCANONICAL_SOURCE_FRAME")
            ledger=st["ledger"]
            for i,item in enumerate(ledger):
                if (type(item) is not dict or
                    set(item)!={"ordinal","selected","before_public_sha256",
                                "after_public_sha256"} or
                    type(item["ordinal"]) is not int or
                    item["ordinal"]!=st["events"]-len(ledger)+i+1 or
                    original_action(item["selected"])!=item["selected"]):
                    raise ValueError("NRM2D_BAD_SELECTED_LEDGER")
                for key in ("before_public_sha256","after_public_sha256"):
                    h=item[key]
                    if type(h) is not str or len(h)!=64 or any(c not in "0123456789abcdef" for c in h):
                        raise ValueError("NRM2D_BAD_PUBLIC_SHA")
                if i and ledger[i-1]["after_public_sha256"]!=item["before_public_sha256"]:
                    raise ValueError("NRM2D_BROKEN_SELECTED_SOURCE_CHAIN")
            if ledger and ledger[-1]["after_public_sha256"]!=digest(current):
                raise ValueError("NRM2D_FINAL_SOURCE_PUBLIC_DRIFT")
            if st["events"] and not ledger:
                raise ValueError("NRM2D_MISSING_SELECTED_SOURCE_LEDGER")
            model=cls()
            model.episodes=st["episodes"]
            model.events=st["events"]
            model.current=current
            model.ledger=ledger
            if model.checkpoint()!=raw:
                raise ValueError("NRM2D_SOURCE_SNAPSHOT_REBUILD_MISMATCH")
            return model
        except (ValueError,TypeError,KeyError,UnicodeError,OverflowError) as e:
            raise ValueError("NRM2D_COLD_SOURCE_REJECTED") from e
