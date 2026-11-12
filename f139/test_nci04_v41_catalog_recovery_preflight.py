"""V41 catalog-only successor preflight: bounded GET and no live mutation."""
from contextlib import closing
from pathlib import Path
import tempfile
import unittest

from f139 import nci04_v41_catalog_recovery_preflight as route
from f139.local_controller import Database, SingleOwner


class V41SourcePreflightTests(unittest.TestCase):
    def provider(self):
        base = "repos/" + route.REPO + "/"
        policy = dict(schema="forge.f139.native-autonomy-feed-owner-policy.v1",
            enabled=True, source_sha=route.OWNER_SOURCE,
            lanes=["Wingless", "Yggdrasil"], max_issue_creations_per_cycle=2,
            require_owner_authored_pr=True,
            require_single_head_commit_delta=True,
            require_single_allowed_source_file=True,
            scientific_first_use=False, new_controller=False,
            new_scheduler=False, new_queue=False, paid_model_calls=0,
            accepted_ref_mutations=0)
        import json
        pages = [
            [dict(number=i, id=10000+i, state="open", labels=[
                dict(name=route.ELIGIBLE_LABEL)]) for i in range(200, 100, -1)],
            [dict(number=i, id=10000+i, state="open", labels=[
                dict(name=route.ELIGIBLE_LABEL)]) for i in range(100, 0, -1)],
            [],
        ]
        data = {
            base + "branches/main": dict(protected=True,
                commit=dict(sha=route.MERGED_REPAIR)),
            base + "compare/" + route.OWNER_SOURCE + "..." +
                route.MERGED_REPAIR + "?per_page=1":
                dict(status="ahead", ahead_by=39, behind_by=0,
                     merge_base_commit=dict(sha=route.OWNER_SOURCE)),
            base + "git/commits/" + route.MERGED_REPAIR:
                dict(sha=route.MERGED_REPAIR, tree=dict(sha="a"*40)),
            base + "compare/" + route.MERGED_REPAIR + "..." +
                route.MERGED_REPAIR + "?per_page=1":
                dict(status="identical", behind_by=0,
                     merge_base_commit=dict(sha=route.MERGED_REPAIR)),
            base + "contents/f139/local_controller.py?ref=" +
                route.MERGED_REPAIR: dict(type="file", sha=route.REPAIR_CONTROLLER_BLOB),
            base + "contents/f139/test_nci04_native_successor_catalog.py?ref=" +
                route.MERGED_REPAIR: dict(type="file", sha=route.REPAIR_NEGATIVE_TEST_BLOB),
            base + "issues/807": dict(state="open", user=dict(login="spoonman136668-ai"),
                                      body=json.dumps(policy)),
            base + "branches/f139-owner-release-" + route.OWNER_SOURCE:
                dict(protected=True, commit=dict(sha=route.OWNER_SOURCE)),
        }
        for i, page in enumerate(pages, 1):
            data[base + "issues?state=open&labels=" + route.ELIGIBLE_LABEL +
                 "&per_page=100&page=" + str(i)] = page
        reads = []
        def get(path):
            reads.append(path)
            return data[path]
        return data, get, reads

    def test_exact_current_protected_source_and_200_issues_admit_readonly_only(self):
        data, get, reads = self.provider()
        state = route.source_preflight(get, route.MERGED_REPAIR)
        self.assertEqual(state["issues_per_page"], [100, 100, 0])
        self.assertEqual(state["unique_eligible_issues"], 200)
        self.assertFalse(state["source_transition_authorized"])
        self.assertFalse(state["scientific_first_use"])
        self.assertEqual(state["remote_writes"], 0)
        self.assertTrue(all(p.startswith("repos/" + route.REPO + "/") for p in reads))
        self.assertEqual(reads.count("repos/" + route.REPO + "/branches/main"), 2)

    def test_wrong_sources_policy_duplicates_extra_items_or_missing_page_fail_closed(self):
        base = "repos/" + route.REPO + "/"
        changes = [
            lambda d: d[base+"branches/main"]["commit"].update(sha="f"*40),
            lambda d: d[base+"issues/807"].update(body="{}"),
            lambda d: d[base+"compare/"+route.OWNER_SOURCE+"..."+
                route.MERGED_REPAIR+"?per_page=1"].update(behind_by=1),
            lambda d: d[base+"contents/f139/local_controller.py?ref="+
                route.MERGED_REPAIR].update(sha="e"*40),
            lambda d: d[base+"issues?state=open&labels="+route.ELIGIBLE_LABEL+
                "&per_page=100&page=2"].__setitem__(0,dict(
                    number=999,id=10101,state="open",
                    labels=[dict(name=route.ELIGIBLE_LABEL)])),
            lambda d: d[base+"issues?state=open&labels="+route.ELIGIBLE_LABEL+
                "&per_page=100&page=3"].append(dict(number=1,id=1,state="open",
                  labels=[dict(name=route.ELIGIBLE_LABEL)])),
        ]
        for change in changes:
            with self.subTest(change=change):
                data, get, _ = self.provider()
                change(data)
                with self.assertRaises(route.V41ReadOnlyDenied):
                    route.source_preflight(get, route.MERGED_REPAIR)
        for bad in (route.OWNER_SOURCE, "not-a-sha", "", None, True):
            with self.subTest(target=bad):
                _, get, reads = self.provider()
                with self.assertRaises(route.V41ReadOnlyDenied):
                    route.source_preflight(get, bad)
                self.assertEqual(reads, [])

    def test_real_readonly_sqlite_without_owner_seal_cannot_be_accepted_or_mutated(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.sqlite"
            with closing(Database.initialize(path, route.OWNER_SOURCE)) as owner:
                prior = owner.meta().copy()
            with closing(Database.open_readonly(path)) as readonly:
                with self.assertRaises(route.V41ReadOnlyDenied):
                    route.original_ledger_preflight(readonly)
                with SingleOwner(path.with_suffix(".lock")):
                    with self.assertRaises(route.V41ReadOnlyDenied):
                        route.original_ledger_preflight(readonly)
                self.assertEqual(readonly.meta(), prior)
                self.assertEqual(readonly.conn.total_changes, 0)
                self.assertEqual(readonly.conn.execute("PRAGMA query_only").fetchone()[0], 1)

    def test_missing_original_database_or_lock_always_denied(self):
        with self.assertRaises(route.V41ReadOnlyDenied):
            route.original_ledger_preflight(None)


if __name__ == "__main__":
    unittest.main()
