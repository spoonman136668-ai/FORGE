"""R37 source-only V2 manifest tests, without GitHub, owner DB or science."""
import base64
import copy
import hashlib
import unittest

from f139.nci04_native_contract import digest
from f139.nci04_r7_package import (
    ALLOWED, R37Denied, freeze_r7_owner_pr, WORKFLOW, PREREG,
)


def blob_sha(raw):
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii")
                        + b"\x00" + raw).hexdigest()


class Fixture:
    def __init__(self, lane):
        self.lane = lane
        self.repo = "spoonman136668-ai/" + lane
        self.root = "repos/" + self.repo
        self.get_count = {}
        self.change_pr = False
        self.change_main = False
        self.routes = {}
        files = []
        blobs = []
        for path in sorted(ALLOWED[lane]):
            raw = ("source-only fixture " + lane + ": " + path + "\n").encode()
            oid = blob_sha(raw)
            files.append({"filename": path, "status": "added",
                          "sha": oid, "changes": 1})
            blobs.append({"path": path, "mode": "100644",
                          "type": "blob", "sha": oid})
            self.routes[self.root + "/git/blobs/" + oid] = {
                "sha": oid, "encoding": "base64", "size": len(raw),
                "content": base64.b64encode(raw).decode("ascii")}
        self.pr_path = self.root + "/pulls/382"
        self.main_path = self.root + "/branches/main"
        self.base_tree_path = self.root + "/git/trees/" + "d"*40 + "?recursive=1"
        self.head_tree_path = self.root + "/git/trees/" + "e"*40 + "?recursive=1"
        self.file_path = self.pr_path + "/files?per_page=6"
        self.routes.update({
            self.pr_path: {
                "number": 382, "id": 38002, "state": "open",
                "author_association": "OWNER", "merged_at": None,
                "user": {"login": "spoonman136668-ai"},
                "changed_files": 5,
                "head": {"sha": "c"*40, "ref": "research/itd01-r7",
                         "repo": {"full_name": self.repo}},
                "base": {"sha": "b"*40, "ref": "main",
                         "repo": {"full_name": self.repo}},
            },
            self.main_path: {"commit": {"sha": "b"*40}},
            self.file_path: files,
            self.root + "/git/commits/" + "b"*40: {
                "sha": "b"*40, "tree": {"sha": "d"*40}},
            self.root + "/git/commits/" + "c"*40: {
                "sha": "c"*40, "tree": {"sha": "e"*40}},
            self.base_tree_path: {
                "sha": "d"*40, "truncated": False,
                "tree": [{"path": "README.md", "mode": "100644",
                          "type": "blob", "sha": "f"*40}]},
            self.head_tree_path: {
                "sha": "e"*40, "truncated": False, "tree": blobs},
        })

    def __call__(self, path):
        assert path in self.routes, "unexpected request: " + path
        self.get_count[path] = self.get_count.get(path, 0) + 1
        doc = copy.deepcopy(self.routes[path])
        if self.change_pr and path == self.pr_path and self.get_count[path] == 2:
            doc["head"]["sha"] = "f"*40
        if self.change_main and path == self.main_path and self.get_count[path] == 2:
            doc["commit"]["sha"] = "f"*40
        return doc


class TestR37Package(unittest.TestCase):
    def setup(self, lane="Wingless"):
        f = Fixture(lane)
        return f, {
            "get": f, "lane": lane, "pr_number": 382,
            "controller_source_sha": "a"*40,
            "semantics": {
                "dependency_sha256": digest(b"deps"),
                "qualification_harness_sha256": digest(b"harness"),
                "training_config_sha256": digest(b"train"),
                "suite_identity_sha256": digest(b"suites"),
                "toolchain_identity": "go1.25.0" if lane == "Wingless" else "python3.11.11",
            }
        }

    def test_two_real_r7_lane_schemas_positive_source_only(self):
        for lane in ("Wingless", "Yggdrasil"):
            with self.subTest(lane=lane):
                f, a = self.setup(lane)
                result = freeze_r7_owner_pr(**a)
                self.assertEqual(result["source_manifest_count"], 5)
                self.assertEqual({v["path"] for v in result["proposal"]["files"]},
                                 set(ALLOWED[lane]))
                self.assertEqual([v["path"] for v in result["proposal"]["files"]],
                                 sorted(ALLOWED[lane]))
                self.assertEqual(result["proposal"]["candidate_head_tree"], "e"*40)
                self.assertEqual(result["proposal"]["target_base_tree"], "d"*40)
                self.assertFalse(result["eligible"])
                self.assertFalse(result["dispatch_authorized"])
                self.assertFalse(result["execute_embedded_workflow"])
                self.assertFalse(result["v1_single_file_compatible"])
                self.assertTrue(result["requires_new_owner_issue_and_worker_contract"])
                self.assertEqual(result["qualification_key"], result["source_evidence_sha256"])
                roles = {v["path"]: v["role"] for v in result["proposal"]["files"]}
                self.assertEqual(roles[WORKFLOW], "workflow-evidence-only")
                self.assertEqual(roles[PREREG], "frozen-preregistration")
                f2, a2 = self.setup(lane)
                self.assertEqual(result, freeze_r7_owner_pr(**a2))

    def test_fail_closed_pr_identity_and_scope(self):
        for name, mut in (
            ("unowned", lambda f: f.routes[f.pr_path]["user"].update(login="outsider")),
            ("not_authorized", lambda f: f.routes[f.pr_path].update(author_association="CONTRIBUTOR")),
            ("too_many", lambda f: f.routes[f.pr_path].update(changed_files=6)),
            ("base_branch", lambda f: f.routes[f.pr_path]["base"].update(ref="feature")),
            ("fork", lambda f: f.routes[f.pr_path]["head"]["repo"].update(full_name="outsider/fork")),
            ("state", lambda f: f.routes[f.pr_path].update(state="closed")),
            ("moved_main", lambda f: f.routes[f.main_path]["commit"].update(sha="f"*40)),
        ):
            with self.subTest(name=name):
                f, a = self.setup()
                mut(f)
                with self.assertRaises(R37Denied):
                    freeze_r7_owner_pr(**a)

    def test_fail_closed_scope_and_tree_custody(self):
        mutations = (
            lambda f: f.routes[f.file_path][0].update(status="modified"),
            lambda f: f.routes[f.file_path][0].update(filename="research/native/itd01/r7/UNREVIEWED.py"),
            lambda f: f.routes[f.file_path][0].update(sha="f"*40),
            lambda f: f.routes[f.file_path].append(copy.deepcopy(f.routes[f.file_path][0])),
            lambda f: f.routes[f.base_tree_path]["tree"].append(
                copy.deepcopy(f.routes[f.head_tree_path]["tree"][0])),
            lambda f: f.routes[f.head_tree_path]["tree"][0].update(mode="120000"),
            lambda f: f.routes[f.head_tree_path].update(truncated=True),
            lambda f: f.routes[f.head_tree_path]["tree"][0].update(sha="f"*40),
            lambda f: f.routes[f.head_tree_path]["tree"].append(
                copy.deepcopy(f.routes[f.head_tree_path]["tree"][0])),
        )
        for mutate in mutations:
            f, a = self.setup()
            mutate(f)
            with self.assertRaises(R37Denied):
                freeze_r7_owner_pr(**a)

    def test_fail_closed_blob_bytes_and_resource_budget(self):
        for mutate in (
            lambda f, p: f.routes[p].update(sha="0"*40),
            lambda f, p: f.routes[p].update(content="INVALID?"),
            lambda f, p: f.routes[p].update(size=0),
            lambda f, p: f.routes[p].update(size=20000),
            lambda f, p: f.routes[p].update(content=" " + f.routes[p]["content"]),
        ):
            f, a = self.setup()
            path = next(k for k in f.routes if "/git/blobs/" in k)
            mutate(f, path)
            with self.assertRaises(R37Denied):
                freeze_r7_owner_pr(**a)

    def test_fail_closed_snapshot_and_semantic_drift(self):
        for which in ("pr", "main"):
            f, a = self.setup()
            if which == "pr":
                f.change_pr = True
            else:
                f.change_main = True
            with self.assertRaises(R37Denied):
                freeze_r7_owner_pr(**a)
        for update in (
            {"pr_number": True}, {"controller_source_sha": "invalid"},
            {"semantics": {"toolchain_identity": "go1.25.0"}},
            {"semantics": {**self.setup()[1]["semantics"], "toolchain_identity":"go1.26.0"}},
            {"semantics": {**self.setup()[1]["semantics"], "suite_identity_sha256":"invalid"}},
        ):
            f, a = self.setup()
            with self.assertRaises(R37Denied):
                freeze_r7_owner_pr(**{**a, **update})


if __name__ == "__main__":
    unittest.main()
