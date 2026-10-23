"""R36 adversarial authenticated source-only discovery tests (no real calls)."""
import base64
import copy
import hashlib
import json
import unittest

from f139.nci04_native_contract import digest, parse_intent
from f139.nci04_pr_discovery import (
    NativePRDiscoveryDenied, prepare_authenticated_pr_proposal,
)
from f139.nci04_proposal_compiler import ProposalPreparationError


def oid(raw):
    return hashlib.sha1(
        b"blob " + str(len(raw)).encode() + b"\x00" + raw).hexdigest()


class Provider:
    def __init__(self, lane="Wingless"):
        repo = ("spoonman136668-ai/Wingless" if lane == "Wingless"
                else "spoonman136668-ai/Yggdrasil")
        path = ("cognition/learned_state.go" if lane == "Wingless"
                else "yggdrasil/memory.py")
        before = (b"package cognition\nconst X = 0\n" if lane == "Wingless"
                  else b"X = 0\n")
        after = (b"package cognition\nconst X = 1\n" if lane == "Wingless"
                 else b"X = 1\n")
        self.before, self.after = before, after
        self.repo = repo
        self.prefix = "repos/" + repo
        self.paths = []
        self.moving = False
        self.pages = {
            self.prefix + "/pulls/48": {
                "number": 48, "id": 48001,
                "state": "open", "merged_at": None,
                "author_association": "OWNER",
                "user": {"login": "spoonman136668-ai"},
                "changed_files": 1,
                "base": {"ref": "main", "sha": "b"*40,
                         "repo": {"full_name": repo}},
                "head": {"ref": "research/candidate", "sha": "c"*40,
                         "repo": {"full_name": repo}},
            },
            self.prefix + "/branches/main": {"commit": {"sha": "b"*40}},
            self.prefix + "/pulls/48/files?per_page=2": [{
                "filename": path, "status": "modified",
                "changes": 1, "sha": oid(after),
            }],
            self.prefix + "/git/commits/" + "b"*40: {
                "sha": "b"*40, "tree": {"sha": "d"*40}},
            self.prefix + "/git/commits/" + "c"*40: {
                "sha": "c"*40, "tree": {"sha": "e"*40}},
            self.prefix + "/contents/" + path + "?ref=" + "b"*40: {
                "type": "file", "size": len(before),
                "encoding": "base64", "content": base64.b64encode(before).decode(),
                "sha": oid(before),
            },
            self.prefix + "/contents/" + path + "?ref=" + "c"*40: {
                "type": "file", "size": len(after),
                "encoding": "base64", "content": base64.b64encode(after).decode(),
                "sha": oid(after),
            },
        }

    def __call__(self, path):
        self.paths.append(path)
        assert path in self.pages, "UNEXPECTED_PROVIDER_FETCH_" + path
        answer = copy.deepcopy(self.pages[path])
        if self.moving and path.endswith("/pulls/48") and self.paths.count(path) == 2:
            answer["head"]["sha"] = "f"*40
        return answer


class TestAuthenticatedPRDiscovery(unittest.TestCase):
    def args(self, lane="Wingless"):
        provider = Provider(lane)
        semantic = {
            "dependency_sha256": digest(b"deps"),
            "qualification_harness_sha256": digest(b"existing-harness"),
            "training_config_sha256": digest(b"training"),
            "suite_identity_sha256": digest(b"focused-and-full-suites"),
            "toolchain_identity": ("go1.25.0" if lane == "Wingless"
                                   else "python3.11.11"),
        }
        return provider, dict(
            get=provider, lane=lane, pr_number=48,
            controller_source_sha="a"*40, semantics=semantic,
        )

    def test_roundtrip_single_path_owner_proposal_no_authority(self):
        for lane in ("Wingless", "Yggdrasil"):
            with self.subTest(lane=lane):
                provider, args = self.args(lane)
                result = prepare_authenticated_pr_proposal(**args)
                doc = json.loads(result["issue_body"])
                raw = base64.b64decode(doc["intent_base64"], validate=True)
                candidate = parse_intent(raw, protected_main="a"*40,
                                         target_commit="b"*40,
                                         target_tree_sha="d"*40)
                self.assertEqual(candidate.after_bytes, provider.after)
                self.assertEqual(candidate.qualification_key, result["qualification_key"])
                self.assertEqual(result["source_evidence"]["head_tree"], "e"*40)
                self.assertEqual(result["source_evidence"]["base_tree"], "d"*40)
                self.assertEqual(result["source_evidence_sha256"],
                                 digest(json.dumps(result["source_evidence"],
                                                   separators=(",", ":"), sort_keys=True,
                                                   ensure_ascii=True).encode("ascii")))
                self.assertFalse(result["eligible"])
                self.assertFalse(result["dispatch_authorized"])
                self.assertFalse(result["automatic_issue_creation"])
                self.assertTrue(result["owner_issue_required"])
                self.assertFalse(result["scientific_first_use"])
                self.assertEqual(len(provider.paths), 8)
                # Idempotent source-only work on the same snapshot.
                provider2, args2 = self.args(lane)
                self.assertEqual(result, prepare_authenticated_pr_proposal(**args2))

    def test_owner_and_repository_forgery_rejected(self):
        scenarios = [
            ("user", lambda p: p.pages[p.prefix + "/pulls/48"]["user"].update(login="visitor")),
            ("association", lambda p: p.pages[p.prefix + "/pulls/48"].update(author_association="CONTRIBUTOR")),
            ("head_repository", lambda p: p.pages[p.prefix + "/pulls/48"]["head"]["repo"].update(full_name="someone/fork")),
            ("base_repository", lambda p: p.pages[p.prefix + "/pulls/48"]["base"]["repo"].update(full_name="someone/fork")),
            ("closed", lambda p: p.pages[p.prefix + "/pulls/48"].update(state="closed")),
            ("changed_file_count", lambda p: p.pages[p.prefix + "/pulls/48"].update(changed_files=2)),
            ("base_branch", lambda p: p.pages[p.prefix + "/pulls/48"]["base"].update(ref="elsewhere")),
            ("base_drift", lambda p: p.pages[p.prefix + "/branches/main"]["commit"].update(sha="f"*40)),
            ("null_pr_id", lambda p: p.pages[p.prefix + "/pulls/48"].update(id=None)),
        ]
        for name, poison in scenarios:
            with self.subTest(name=name):
                provider, args = self.args()
                poison(provider)
                with self.assertRaises(NativePRDiscoveryDenied):
                    prepare_authenticated_pr_proposal(**args)

    def test_modified_file_must_be_one_and_path_safe(self):
        for edit in (
            lambda a: a.update(status="added"),
            lambda a: a.update(filename="research/native/extra.go"),
            lambda a: a.update(filename="cognition/../danger.go"),
            lambda a: a.update(filename="cognition/.hidden.go"),
            lambda a: a.update(changes=0),
            lambda a: a.update(sha="INVALID"),
            lambda a: a.update(sha="f"*40),
        ):
            with self.subTest(edit=repr(edit)):
                provider, args = self.args()
                edit(provider.pages[provider.prefix + "/pulls/48/files?per_page=2"][0])
                with self.assertRaises(NativePRDiscoveryDenied):
                    prepare_authenticated_pr_proposal(**args)
        provider, args = self.args()
        provider.pages[provider.prefix + "/pulls/48/files?per_page=2"].append(
            copy.deepcopy(provider.pages[provider.prefix + "/pulls/48/files?per_page=2"][0]))
        with self.assertRaises(NativePRDiscoveryDenied):
            prepare_authenticated_pr_proposal(**args)

    def test_provider_commit_and_file_bytes_not_accepted_on_appearance(self):
        poisoners = [
            lambda p: p.pages[p.prefix + "/git/commits/" + "b"*40].update(sha="f"*40),
            lambda p: p.pages[p.prefix + "/git/commits/" + "c"*40].update(tree={"sha":"INVALID"}),
            lambda p: p.pages[p.prefix + "/contents/cognition/learned_state.go?ref=" + "c"*40].update(sha="f"*40),
            lambda p: p.pages[p.prefix + "/contents/cognition/learned_state.go?ref=" + "b"*40].update(size=100),
            lambda p: p.pages[p.prefix + "/contents/cognition/learned_state.go?ref=" + "c"*40].update(content="@@@"),
            lambda p: p.pages[p.prefix + "/contents/cognition/learned_state.go?ref=" + "c"*40].update(content=" " + base64.b64encode(p.after).decode()),
        ]
        for poison in poisoners:
            provider, args = self.args()
            poison(provider)
            with self.assertRaises(NativePRDiscoveryDenied):
                prepare_authenticated_pr_proposal(**args)

    def test_pr_move_during_read_is_rejected(self):
        provider, args = self.args()
        provider.moving = True
        with self.assertRaisesRegex(NativePRDiscoveryDenied, "PR_MOVED"):
            prepare_authenticated_pr_proposal(**args)

    def test_semantic_contract_and_input_bounds(self):
        provider, args = self.args()
        variants = [
            {"pr_number": True}, {"pr_number": 0}, {"lane": "Other"},
            {"controller_source_sha": "x"*40},
            {"semantics": {**args["semantics"], "suite_identity_sha256":"invalid"}},
            {"semantics": {**args["semantics"], "toolchain_identity":"go1.26.0"}},
            {"semantics": {**args["semantics"], "extra":"x"}},
        ]
        for overrides in variants:
            with self.subTest(overrides=overrides):
                with self.assertRaises((NativePRDiscoveryDenied, ProposalPreparationError)):
                    prepare_authenticated_pr_proposal(**{**args, **overrides})


if __name__ == "__main__":
    unittest.main()
