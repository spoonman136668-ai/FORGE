"""K4B in-memory source overlay. NEVER changes the pinned upstream checkout.

Used only on the isolated development replay runner. The original K4A harness and
upstream git source identity stay unchanged; the precise candidate is source-
qualified before import and compiled under the original module filename.
"""
import hashlib
import importlib.abc
import importlib.machinery
from pathlib import Path
import sys
from k4b_replay_state_repair import source_replace

PINNED_GIT_BLOB = "6169fcd629e5721e889fbcada52c06e9c2a37b0e"
TARGET = "causal_world.envs.causalworld"


class CandidateLoader(importlib.machinery.SourceFileLoader):
    def get_code(self, fullname):
        if fullname != TARGET:
            raise RuntimeError("UNEXPECTED_OVERLAY_TARGET")
        raw = Path(self.path).read_bytes()
        original_blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
        if original_blob != PINNED_GIT_BLOB:
            raise RuntimeError("K4B_PINNED_SOURCE_BLOB_DRIFT:" + original_blob)
        candidate = source_replace(raw.decode("utf-8"))
        digest = hashlib.sha256(candidate.encode("utf-8")).hexdigest()
        print("K4B_INMEMORY_OVERLAY_VERIFIED=" + digest, flush=True)
        return compile(candidate, self.path, "exec", dont_inherit=True)


class CandidateFinder(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path, target=None):
        if fullname != TARGET:
            return None
        native = importlib.machinery.PathFinder.find_spec(fullname, path)
        if not native or not isinstance(native.loader, importlib.machinery.SourceFileLoader):
            raise RuntimeError("K4B_TARGET_SOURCE_NOT_FOUND")
        if Path(native.origin).name != "causalworld.py":
            raise RuntimeError("K4B_MODULE_IDENTITY_DRIFT")
        native.loader = CandidateLoader(fullname, native.origin)
        return native


sys.meta_path.insert(0, CandidateFinder())
