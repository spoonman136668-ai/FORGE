"""Remote issue created during maintenance wait must block before owner pause."""
from contextlib import closing
import inspect
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from f139.local_controller import Database, GitHub, F139Error
from f139 import nci04_v38_source_transition as contract
from f139 import nci04_v32_original_owner_transition_cli as shared
from f139 import nci04_v38_original_owner_transition_cli as cli
from f139.nci04_native_contract import canonical
from f139.nci04_owner_issue import inspect_owner_issue
from f139.test_nci04_native_successor_catalog import source_issue, MAIN, TARGET, TREE


class HandoffCatalogTests(unittest.TestCase):
    def api(self, snapshots):
        calls = []
        snapshots = iter(snapshots)
        def runner(args):
            calls.append(tuple(args))
            if args == ['repos/spoonman136668-ai/FORGE/issues?state=open&labels=f139-native-development-eligible&per_page=100&page=1']:
                return canonical(next(snapshots))
            if args == ['repos/spoonman136668-ai/Wingless/git/commits/'+TARGET]:
                return canonical(dict(sha=TARGET,tree=dict(sha=TREE)))
            raise AssertionError('non-catalog or non-GET route: '+repr(args))
        return GitHub(runner=runner), calls

    def test_empty_intake_is_query_only_and_has_no_dispatch_authority(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'state.sqlite'
            with closing(Database.initialize(path,MAIN)):
                pass
            with closing(Database.open_readonly(path)) as db:
                before=db.meta().copy();changes=db.conn.total_changes
                api,calls=self.api([[]])
                out=shared.require_no_unadmitted_native_issues(db,api,contract)
                self.assertEqual(out['unadmitted_issues'],0)
                self.assertFalse(out['dispatch_authorized'])
                self.assertEqual(db.meta(),before)
                self.assertEqual(db.conn.total_changes,changes)
                self.assertEqual(len(calls),1)
                self.assertEqual(db.conn.execute('PRAGMA query_only').fetchone()[0],1)

    def test_proposal_created_during_wait_blocks_at_first_post_mutex_read(self):
        with tempfile.TemporaryDirectory() as td,closing(Database.initialize(
                Path(td)/'state.sqlite',MAIN)) as db:
            before=db.meta().copy();api,calls=self.api([[source_issue(MAIN,1516,6245813791)]])
            # This proposal has a valid current/predecessor source and immutable
            # target, but there is no NATIVE_DEVELOPMENT_ADMITTED ledger event.
            with self.assertRaisesRegex(contract.MaintenanceDenied,'UNADMITTED_NATIVE_ISSUE_AT_HANDOFF'):
                shared.require_no_unadmitted_native_issues(db,api,contract)
            self.assertEqual(db.meta(),before)
            self.assertEqual(len(calls),2)

    def test_preflight_rechecks_after_wait_and_never_rehearses_a_pending_proposal(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'state.sqlite'
            with closing(Database.initialize(path,MAIN)) as original:
                before=original.meta().copy()
            api,calls=self.api([[source_issue(MAIN,1516,6245813791)]])
            with patch('f139.local_controller.GitHub',return_value=api), \
                    patch('f139.nci04_partial_publication_custody.verify_remote_readback'), \
                    patch.object(contract,'readonly_snapshot',return_value={}), \
                    patch.object(cli,'rehearse_private_history') as rehearsal, \
                    patch.object(cli,'guarded_transition') as transition:
                with self.assertRaisesRegex(contract.MaintenanceDenied,'UNADMITTED_NATIVE_ISSUE_AT_HANDOFF'):
                    cli.main(['--db',str(path),'--target','e'*40,'--preflight-only','--rehearse-copy'])
                rehearsal.assert_not_called();transition.assert_not_called()
            with closing(Database.open_readonly(path)) as cold:
                self.assertEqual(cold.meta(),before)
            self.assertEqual(len(calls),2)

    def test_second_check_detects_a_proposal_created_after_early_preflight(self):
        with tempfile.TemporaryDirectory() as td,closing(Database.initialize(
                Path(td)/'state.sqlite',MAIN)) as db:
            api,_=self.api([[],[source_issue(MAIN,1516,6245813791)]])
            shared.require_no_unadmitted_native_issues(db,api,contract)
            with self.assertRaisesRegex(contract.MaintenanceDenied,'UNADMITTED_NATIVE_ISSUE_AT_HANDOFF'):
                shared.require_no_unadmitted_native_issues(db,api,contract)
        source=inspect.getsource(shared.guarded_transition)
        check=source.index('require_no_unadmitted_native_issues(db, api, contract)')
        self.assertGreater(check,source.index('rehearse_generator(copy, api, target)'))
        self.assertLess(check,source.index('result = commit_transition(db, proof'))

    def test_exact_historical_identity_is_reverified_and_excluded_without_withdrawal(self):
        old=source_issue(MAIN,1514,6244985561)
        parsed=inspect_owner_issue(old,protected_main=MAIN,
            authenticated_target_commit=TARGET,authenticated_target_tree=TREE)
        event=dict(issue_number=parsed.number,issue_id=parsed.issue_id,
            source_sha=parsed.source_sha,issue_body_sha256=parsed.issue_body_sha256,ticket=parsed.ticket)
        with tempfile.TemporaryDirectory() as td,closing(Database.initialize(
                Path(td)/'state.sqlite',MAIN)) as db:
            db.event('NATIVE_DEVELOPMENT_ADMITTED',event)
            api,calls=self.api([[old],[{**old,'id':old['id']+1}]])
            # This fixture tests only native_events->catalog identity plumbing.
            # Authentic full original custody is checked by db.verify in production.
            with patch.object(db,'verify'):
                self.assertEqual(shared.require_no_unadmitted_native_issues(db,api,contract)['unadmitted_issues'],0)
                with self.assertRaisesRegex(F139Error,'NATIVE_HISTORICAL_ISSUE_DRIFT'):
                    shared.require_no_unadmitted_native_issues(db,api,contract)
            self.assertTrue(all(len(args)==1 for args in calls))

    def test_unknown_stale_source_and_read_failure_are_not_empty_intake(self):
        with tempfile.TemporaryDirectory() as td,closing(Database.initialize(
                Path(td)/'state.sqlite',MAIN)) as db:
            before=db.meta().copy()
            api,_=self.api([[source_issue('9'*40,1516,6245813791)]])
            with self.assertRaisesRegex(F139Error,'NATIVE_ISSUE_OR_SOURCE_REJECTED'):
                shared.require_no_unadmitted_native_issues(db,api,contract)
            api=GitHub(runner=lambda args: (_ for _ in ()).throw(F139Error('F139_GITHUB_API_FAILED')))
            with self.assertRaisesRegex(F139Error,'GITHUB_API_FAILED'):
                shared.require_no_unadmitted_native_issues(db,api,contract)
            self.assertEqual(db.meta(),before)


if __name__=='__main__':unittest.main()
