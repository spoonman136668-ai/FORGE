from __future__ import annotations
import base64
import hashlib
import json
import unittest

from f139.local_controller import GitHub
from f139.nci04_autonomy_feed import (
    POLICY_ISSUE, POLICY_SCHEMA, TITLE_PREFIX, NativeFeedDenied,
    inspect_policy, prepare_feed,
)


def blob(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


class FakeProvider:
    def __init__(self):
        self.source = "a" * 40
        self.parent = "b" * 40
        self.head = "c" * 40
        self.parent_tree = "d" * 40
        self.head_tree = "e" * 40
        self.path = "cognition/continual.go"
        self.before = b"package cognition\nfunc Old(){}\n"
        self.after = b"package cognition\nfunc Old(){ panic(\"bounded\") }\n"
        self.pr = {
            "number": 383, "id": 900383, "state": "open", "draft": True,
            "title": TITLE_PREFIX + " bounded owner candidate",
            "author_association": "OWNER",
            "user": {"login": "spoonman136668-ai"},
            "head": {"sha": self.head,
                     "repo": {"full_name": "spoonman136668-ai/Wingless"}},
            "base": {"sha": "f" * 40},
        }
        self.policy = {
            "schema": POLICY_SCHEMA, "enabled": True, "source_sha": self.source,
            "title_prefix": TITLE_PREFIX, "lanes": ["Wingless", "Yggdrasil"],
            "max_issue_creations_per_cycle": 2,
            "require_owner_authored_pr": True,
            "require_single_head_commit_delta": True,
            "require_single_allowed_source_file": True,
            "scientific_first_use": False, "paid_model_calls": 0,
            "accepted_ref_mutations": 0, "new_controller": False,
            "new_scheduler": False, "new_queue": False,
        }

    def issue(self):
        return {
            "number": POLICY_ISSUE, "id": 807, "state": "open",
            "author_association": "OWNER",
            "user": {"login": "spoonman136668-ai"},
            "body": json.dumps(self.policy, separators=(",", ":")),
        }

    def content(self, raw):
        return {"type": "file", "encoding": "base64", "size": len(raw),
                "sha": blob(raw), "content": base64.b64encode(raw).decode("ascii")}

    def get(self, route):
        if route == "repos/spoonman136668-ai/FORGE/issues/807":
            return self.issue()
        if route == "repos/spoonman136668-ai/Wingless/pulls?state=open&per_page=100&page=1":
            return [self.pr]
        if route == "repos/spoonman136668-ai/Yggdrasil/pulls?state=open&per_page=100&page=1":
            return []
        if route == "repos/spoonman136668-ai/Wingless/pulls/383":
            return self.pr
        if route == "repos/spoonman136668-ai/Wingless/git/commits/" + self.head:
            return {"sha": self.head, "tree": {"sha": self.head_tree},
                    "parents": [{"sha": self.parent}]}
        if route == "repos/spoonman136668-ai/Wingless/git/commits/" + self.parent:
            return {"sha": self.parent, "tree": {"sha": self.parent_tree},
                    "parents": [{"sha": "1" * 40}]}
        if route == ("repos/spoonman136668-ai/Wingless/compare/" +
                     self.parent + "..." + self.head):
            return {
                "status": "ahead", "ahead_by": 1, "behind_by": 0,
                "total_commits": 1,
                "files": [{"status": "modified", "changes": 1,
                           "filename": self.path, "sha": blob(self.after)}],
            }
        if route == ("repos/spoonman136668-ai/Wingless/contents/" +
                     self.path + "?ref=" + self.parent):
            return self.content(self.before)
        if route == ("repos/spoonman136668-ai/Wingless/contents/" +
                     self.path + "?ref=" + self.head):
            return self.content(self.after)
        raise AssertionError("unexpected route " + route)


class FakePublicHybridProvider(FakeProvider):
    """Hybrid owner PR, using the exact existing feeder/provider read protocol."""
    def __init__(self):
        super().__init__()
        self.path = "native_p64k_public_probe.py"
        self.before = b"def causal_update(state):\n    return state\n"
        self.after = b"def causal_update(state):\n    return state + 1\n"
        self.pr["head"]["repo"]["full_name"] = "spoonman136668-ai/TTT-Hybrid-Lab"
        self.policy["lanes"] = ["Wingless", "Yggdrasil", "TTT-Hybrid"]
        self.metadata = {
            "full_name": "spoonman136668-ai/TTT-Hybrid-Lab",
            "private": False, "visibility": "public",
        }
        self.routes = []

    def get(self, route):
        self.routes.append(route)
        hybrid = "repos/spoonman136668-ai/TTT-Hybrid-Lab"
        wingless = "repos/spoonman136668-ai/Wingless"
        if route == hybrid:
            return self.metadata
        if route == wingless + "/pulls?state=open&per_page=100&page=1":
            return []
        if route.startswith(hybrid + "/"):
            return super().get(wingless + route[len(hybrid):])
        return super().get(route)


class NativeAutonomyFeedTests(unittest.TestCase):
    def test_enabled_owner_single_commit_source_candidate_compiles_v1_issue(self):
        p = FakeProvider()
        report = prepare_feed(p.get, source_sha=p.source,
                              existing_candidate_identities=set())
        self.assertTrue(report["enabled"])
        self.assertEqual(len(report["candidates"]), 1)
        self.assertEqual(report["rejected"], [])
        c = report["candidates"][0]
        self.assertEqual(c["pr_number"], 383)
        self.assertEqual(c["lane"], "Wingless")
        body = json.loads(c["issue_body"])
        self.assertEqual(body["schema"],
                         "forge.f139.nci04.owner-native-development.v1")
        self.assertFalse(body["scientific_first_use"])
        self.assertEqual(body["paid_model_calls"], 0)
        intent = json.loads(base64.b64decode(body["intent_base64"], validate=True))
        self.assertEqual(intent["target_commit"], p.parent)
        self.assertEqual(intent["target_tree_sha"], p.parent_tree)
        self.assertEqual(intent["path"], p.path)
        self.assertEqual(base64.b64decode(intent["after_base64"]), p.after)
        self.assertFalse(intent["scientific_first_use"])
        self.assertEqual(intent["accepted_ref_mutations"], 0)
        self.assertEqual(intent["paid_api_calls"], 0)

    def test_disabled_policy_is_inert(self):
        p = FakeProvider()
        p.policy["enabled"] = False
        self.assertEqual(
            prepare_feed(p.get, source_sha=p.source,
                         existing_candidate_identities=set()),
            {"enabled": False, "candidates": [], "rejected": []})

    def test_policy_source_drift_fails_closed(self):
        p = FakeProvider()
        with self.assertRaisesRegex(NativeFeedDenied, "POLICY_SCOPE_DRIFT"):
            prepare_feed(p.get, source_sha="9" * 40,
                         existing_candidate_identities=set())

    def test_non_owner_matching_pr_is_rejected_not_executed(self):
        p = FakeProvider()
        p.pr["user"] = {"login": "attacker"}
        report = prepare_feed(p.get, source_sha=p.source,
                              existing_candidate_identities=set())
        self.assertEqual(report["candidates"], [])
        self.assertRegex(report["rejected"][0]["reason"],
                         "PR_NOT_EXPLICIT_OWNER_CANDIDATE")

    def test_multi_file_or_multi_commit_delta_is_rejected(self):
        p = FakeProvider()
        original = p.get
        def get(route):
            value = original(route)
            if "/compare/" in route:
                value = dict(value, total_commits=2, ahead_by=2)
            return value
        report = prepare_feed(get, source_sha=p.source,
                              existing_candidate_identities=set())
        self.assertEqual(report["candidates"], [])
        self.assertRegex(report["rejected"][0]["reason"],
                         "HEAD_DELTA_NOT_EXACTLY_ONE_COMMIT_FILE")

    def test_disallowed_source_path_is_rejected(self):
        p = FakeProvider()
        p.path = ".github/workflows/pwn.yml"
        report = prepare_feed(p.get, source_sha=p.source,
                              existing_candidate_identities=set())
        self.assertEqual(report["candidates"], [])
        self.assertRegex(report["rejected"][0]["reason"],
                         "HEAD_FILE_NOT_ALLOWED_MODIFICATION")

    def test_existing_exact_intent_is_deduped(self):
        p = FakeProvider()
        first = prepare_feed(p.get, source_sha=p.source,
                             existing_candidate_identities=set())
        known = {first["candidates"][0]["candidate_identity"]}
        second = prepare_feed(p.get, source_sha=p.source,
                              existing_candidate_identities=known)
        self.assertEqual(second["candidates"], [])

    def test_same_patch_dedupes_even_if_provenance_intent_changes(self):
        p = FakeProvider()
        first = prepare_feed(p.get, source_sha=p.source,
                             existing_candidate_identities=set())
        identity = first["candidates"][0]["candidate_identity"]
        # Dedupe is the immutable patch, not compiler metadata/intent bytes.
        self.assertEqual(
            prepare_feed(p.get, source_sha=p.source,
                         existing_candidate_identities={identity})["candidates"],
            [])

    def test_nonprefixed_owner_pr_is_ignored(self):
        p = FakeProvider()
        p.pr["title"] = "ordinary draft"
        report = prepare_feed(p.get, source_sha=p.source,
                              existing_candidate_identities=set())
        self.assertEqual(report["candidates"], [])
        self.assertEqual(report["rejected"], [])

    def test_provider_compare_route_allowed_but_path_traversal_denied(self):
        seen = []
        api = GitHub(runner=lambda args: (
            seen.append(args[0]) or b'{"status":"ahead"}'))
        route = ("repos/spoonman136668-ai/Wingless/compare/" +
                 "a"*40 + "..." + "b"*40)
        self.assertEqual(api.native_repo_get(route), {"status": "ahead"})
        self.assertEqual(seen, [route])
        with self.assertRaisesRegex(Exception, "NATIVE_FEED_ROUTE_INVALID"):
            api.native_repo_get(
                "repos/spoonman136668-ai/Wingless/contents/../secret")

    def test_real_native_reader_accepts_exact_hybrid_repository_get_routes(self):
        # Exercise the real transport boundary; feeder FakeProvider alone
        # cannot detect a missing repository in GitHub.native_repo_get.
        seen = []
        api = GitHub(runner=lambda args: (seen.append(args) or b'{"private":true}'))
        prefix = "repos/spoonman136668-ai/TTT-Hybrid-Lab/"
        for suffix in ("branches/main", "git/commits/"+"a"*40,
                       "pulls?state=open&per_page=100", "pulls/55/files?per_page=100",
                       "contents/scripts/native_qualified_policy.py?ref="+"b"*40,
                       "compare/"+"a"*40+"..."+"b"*40+"?per_page=1&page=2"):
            route = prefix+suffix
            self.assertEqual(api.native_repo_get(route), {"private": True})
            self.assertEqual(seen[-1], [route])
        self.assertEqual(api.native_repo_get(prefix[:-1]), {"private": True})
        self.assertEqual(seen[-1], [prefix[:-1]])
        self.assertEqual(len(seen), 7)
        before = list(seen)
        for route in (prefix+"contents/../secret", prefix+"contents/..",
                      prefix+"contents/unsafe\\file", prefix+"contents/unsafe file",
                      "https://api.github.com/"+prefix+"branches/main",
                      "repos/foreign/TTT-Hybrid-Lab/branches/main",
                      "repos/spoonman136668-ai/TTT-Hybrid-Lab-other/branches/main",
                      "repos/spoonman136668-ai/K-Terminal/branches/main",
                      "--method POST"):
            with self.subTest(route=route), self.assertRaisesRegex(Exception, "NATIVE_FEED_ROUTE_INVALID"):
                api.native_repo_get(route)
        self.assertEqual(seen, before)

    def publication_case(self, lane, *, visibility=False, fullname=None):
        from f139.nci04_proposal_compiler import prepare_proposal
        from f139.nci04_owner_issue import LABEL
        from f139.nci04_native_contract import REPOS
        repo = REPOS[lane][0]
        toolchain = "go1.25.0" if lane == "Wingless" else "python3.11.11"
        private = lane != "Wingless"
        before = b"def after_action():\n    return None\n" if private else b"package cognition\nfunc Old(){}\n"
        after = b"def after_action():\n    return 1 # synthetic private marker\n" if private else b"package cognition\nfunc Old(){ println(1) }\n"
        proposal = prepare_proposal(controller_source_sha="a"*40, lane=lane,
            target_commit="b"*40, target_tree_sha="c"*40,
            path="scripts/native_qualified_policy.py" if private else "cognition/continual.go",
            before=before, after=after, dependency_sha256="d"*64,
            qualification_harness_sha256="e"*64, training_config_sha256="f"*64,
            suite_identity_sha256="1"*64, toolchain_identity=toolchain)
        body = proposal["issue_body"]
        # Existing public issue bytes really contain the complete patch;
        # encoding is not a confidentiality boundary.
        intent = json.loads(base64.b64decode(json.loads(body)["intent_base64"]))
        self.assertEqual(base64.b64decode(intent["after_base64"]), after)
        seen = []
        def runner(args):
            seen.append(args)
            if args[0] == "--method":
                return json.dumps(dict(state="open",number=1,id=2,
                    user=dict(login="spoonman136668-ai"),author_association="OWNER",
                    body=body,labels=[dict(name=LABEL)])).encode()
            metadata=dict(full_name=repo if fullname is None else fullname,
                          private=visibility)
            if lane == "TTT-Hybrid":
                metadata["visibility"] = "private" if visibility else "public"
            return json.dumps(metadata).encode()
        return GitHub(runner=runner), seen, body, repo

    def test_private_source_patch_is_never_posted_to_public_owner_issue(self):
        api, seen, body, repo = self.publication_case("TTT-Hybrid", visibility=True)
        with self.assertRaisesRegex(Exception, "HYBRID_PUBLIC_VISIBILITY_NOT_AUTHENTICATED"):
            api.create_native_feed_issue(title="F139 auto-feed TTT-Hybrid PR#1",body=body)
        self.assertEqual(seen, [["repos/"+repo]])
        self.assertFalse(any(args[0] == "--method" for args in seen))

    def test_public_source_publication_preserves_existing_two_lane_path(self):
        for lane in ("Wingless","Yggdrasil"):
            api, seen, body, repo = self.publication_case(lane)
            result=api.create_native_feed_issue(title="F139 auto-feed "+lane+" PR#1",body=body)
            self.assertEqual(result["body"],body)
            self.assertEqual(seen[0],["repos/"+repo])
            self.assertEqual(seen[1][:3],["--method","POST","repos/spoonman136668-ai/FORGE/issues"])

    def test_visibility_missing_wrong_identity_and_read_failure_never_publish(self):
        for value in (True,None,"false",0):
            api, seen, body, _ = self.publication_case("Wingless", visibility=value)
            with self.subTest(value=value),self.assertRaisesRegex(Exception,"NATIVE_FEED_SOURCE_NOT_VERIFIED_PUBLIC"):
                api.create_native_feed_issue(title="F139 auto-feed Wingless PR#1",body=body)
            self.assertEqual(len(seen),1)
        api, seen, body, _ = self.publication_case("Wingless",fullname="foreign/repo")
        with self.assertRaisesRegex(Exception,"NATIVE_FEED_SOURCE_NOT_VERIFIED_PUBLIC"):
            api.create_native_feed_issue(title="F139 auto-feed Wingless PR#1",body=body)
        self.assertEqual(len(seen),1)
        def unavailable(args):
            seen.append(args)
            raise RuntimeError("metadata unavailable")
        api.runner=unavailable;seen.clear()
        with self.assertRaisesRegex(RuntimeError,"metadata unavailable"):
            api.create_native_feed_issue(title="F139 auto-feed Wingless PR#1",body=body)
        self.assertEqual(len(seen),1)
        for broken in ('{}', 'null', '{', json.dumps({"lane":"Wingless","intent_base64":"bad"})):
            seen.clear()
            with self.assertRaisesRegex(Exception,"NATIVE_FEED_PUBLICATION_INTENT_INVALID"):
                api.create_native_feed_issue(title="F139 auto-feed Wingless PR#1",body=broken)
            self.assertEqual(seen,[])
        record=json.loads(body)
        for key,value in (("lane","TTT-Hybrid"),("target_repository","spoonman136668-ai/TTT-Hybrid-Lab")):
            intent=json.loads(base64.b64decode(record["intent_base64"]))
            intent[key]=value
            bad={**record,"intent_base64":base64.b64encode(json.dumps(intent).encode()).decode()}
            seen.clear()
            with self.subTest(key=key),self.assertRaisesRegex(Exception,"NATIVE_FEED_PUBLICATION_INTENT_INVALID"):
                api.create_native_feed_issue(title="F139 auto-feed Wingless PR#1",body=json.dumps(bad))
            self.assertEqual(seen,[])

    def test_public_hybrid_real_feeder_uses_authenticated_source_bytes(self):
        p = FakePublicHybridProvider()
        report = prepare_feed(p.get, source_sha=p.source,
                              existing_candidate_identities=set())
        self.assertTrue(report["enabled"])
        self.assertEqual(report["rejected"], [])
        self.assertEqual(len(report["candidates"]), 1)
        candidate = report["candidates"][0]
        self.assertEqual(candidate["lane"], "TTT-Hybrid")
        self.assertEqual(candidate["pr_number"], 383)
        intent = json.loads(base64.b64decode(
            json.loads(candidate["issue_body"])["intent_base64"],validate=True))
        self.assertEqual(intent["path"], p.path)
        self.assertEqual(base64.b64decode(intent["after_base64"]),p.after)
        self.assertEqual(intent["target_commit"],p.parent)
        self.assertFalse(intent["scientific_first_use"])
        self.assertEqual(p.routes.count("repos/spoonman136668-ai/TTT-Hybrid-Lab"),1)
        self.assertLess(
            p.routes.index("repos/spoonman136668-ai/TTT-Hybrid-Lab"),
            next(i for i,x in enumerate(p.routes) if "/git/commits/" in x))

    def test_private_internal_spoofed_or_ambiguous_hybrid_metadata_cannot_read_patch(self):
        repository="spoonman136668-ai/TTT-Hybrid-Lab"
        for metadata in (
            {"full_name":repository,"private":True,"visibility":"private"},
            {"full_name":repository,"private":False,"visibility":"internal"},
            {"full_name":repository,"private":False},
            {"full_name":"foreign/TTT-Hybrid-Lab","private":False,"visibility":"public"},
            {"full_name":repository,"private":0,"visibility":"public"},
            {"full_name":repository,"private":"false","visibility":"public"},
            None,
        ):
            with self.subTest(metadata=metadata):
                p=FakePublicHybridProvider()
                p.metadata=metadata
                report=prepare_feed(p.get,source_sha=p.source,
                                    existing_candidate_identities=set())
                self.assertEqual(report["candidates"],[])
                self.assertEqual(len(report["rejected"]),1)
                self.assertIn("HYBRID_PUBLIC_VISIBILITY_NOT_AUTHENTICATED",
                              report["rejected"][0]["reason"])
                self.assertFalse(any("/contents/" in x or "/git/commits/" in x
                                     for x in p.routes))
        p=FakePublicHybridProvider()
        p.pr["user"]={"login":"attacker"}
        report=prepare_feed(p.get,source_sha=p.source,
                            existing_candidate_identities=set())
        self.assertEqual(report["candidates"],[])
        self.assertIn("PR_NOT_EXPLICIT_OWNER_CANDIDATE",
                      report["rejected"][0]["reason"])
        self.assertNotIn("repos/"+repository,p.routes)

    def test_public_hybrid_publication_rechecks_classification_and_keeps_original_workflow(self):
        api, seen, body, repo=self.publication_case("TTT-Hybrid",visibility=False)
        result=api.create_native_feed_issue(
            title="F139 auto-feed TTT-Hybrid PR#1",body=body)
        self.assertEqual(result["body"],body)
        self.assertEqual(seen[0],["repos/"+repo])
        self.assertEqual(seen[1][:3],["--method","POST",
                                      "repos/spoonman136668-ai/FORGE/issues"])
        original=api.runner
        for metadata in (
            {"full_name":repo,"private":True,"visibility":"private"},
            {"full_name":repo,"private":False,"visibility":"internal"},
            {"full_name":repo,"private":False},
            {"full_name":"foreign/repo","private":False,"visibility":"public"},
        ):
            seen.clear()
            def changed(args):
                if args == ["repos/"+repo]:
                    seen.append(args)
                    return json.dumps(metadata).encode()
                return original(args)
            api.runner=changed
            with self.subTest(metadata=metadata),self.assertRaisesRegex(
                    Exception,"HYBRID_PUBLIC_VISIBILITY_NOT_AUTHENTICATED"):
                api.create_native_feed_issue(
                    title="F139 auto-feed TTT-Hybrid PR#1",body=body)
            self.assertEqual(seen,[["repos/"+repo]])
        api.runner=original


    def test_staged_third_lane_does_not_enter_original_native_feeder(self):
        p = FakeProvider()
        baseline = prepare_feed(
            p.get, source_sha=p.source,
            existing_candidate_identities=set())
        self.assertEqual(len(baseline["candidates"]), 1)
        p.policy["lanes"] = ["Wingless", "Yggdrasil", "FORGE-self"]
        expanded = prepare_feed(
            p.get, source_sha=p.source,
            existing_candidate_identities=set())
        self.assertEqual(expanded, baseline)
        self.assertEqual(expanded["candidates"][0]["lane"], "Wingless")
        self.assertEqual(expanded["rejected"], [])

    def test_expanded_scope_is_exact_and_native_lanes_cannot_change(self):
        p = FakeProvider()
        for lanes in (
            ["Wingless", "FORGE-self"],
            ["FORGE-self", "Wingless", "Yggdrasil"],
            ["Wingless", "Yggdrasil", "FORGE-self", "FORGE-self"],
            ["Wingless", "Yggdrasil", "Qualification"],
            ["Wingless", "Yggdrasil", "Hybrid"],
            ["Wingless", "Yggdrasil", "FORGE-self", "Hybrid"],
            "Wingless",
            None,
        ):
            with self.subTest(lanes=lanes):
                p.policy["lanes"] = lanes
                with self.assertRaisesRegex(
                        NativeFeedDenied, "POLICY_SCOPE_DRIFT"):
                    inspect_policy(p.issue(), p.source)
        p.policy["lanes"] = ["Wingless", "Yggdrasil", "FORGE-self"]
        self.assertEqual(
            inspect_policy(p.issue(), p.source)["lanes"],
            p.policy["lanes"])

    def test_policy_cannot_turn_on_science_or_new_scheduler(self):
        p = FakeProvider()
        for field, value in (("scientific_first_use", True),
                             ("paid_model_calls", 1),
                             ("accepted_ref_mutations", 1),
                             ("new_controller", True),
                             ("new_scheduler", True),
                             ("new_queue", True),
                             ("max_issue_creations_per_cycle", 3)):
            q = FakeProvider()
            q.policy[field] = value
            with self.subTest(field=field), self.assertRaisesRegex(
                    NativeFeedDenied, "POLICY_SCOPE_DRIFT"):
                inspect_policy(q.issue(), q.source)


if __name__ == "__main__":
    unittest.main()
