"""Failure-parent exclusion; synthetic custody tests are not live acceptance."""
import base64
import unittest
from unittest.mock import patch

from f139 import nci04_model_free_search as search
from f139 import nci04_genenv_owner_backend as backend
from f139.nci04_native_contract import canonical, digest
from f139.nci04_prompt_program import SEED, ProgramRejected, recover_program, build_plan
from f139.test_nci04_prompt_program import BEFORE, LEGACY, plan
from f139 import test_nci04_model_free_search as owner_fixtures
from f139 import test_nci04_genenv_owner_backend as backend_fixtures


class ParentSelectionTests(unittest.TestCase):
    def test_failed_program_stays_consumed_but_cannot_be_a_parent(self):
        child = plan().bindings[0].source.after
        sources = LEGACY + (child,)
        historical = plan(sources)
        self.assertEqual(historical.parent_program, recover_program(BEFORE, child))
        filtered = plan(sources, eligible_parent_sha256=frozenset())
        self.assertEqual(filtered.parent_program, SEED)
        self.assertNotIn(digest(child), [b.source.after_sha256 for b in filtered.bindings])
        self.assertNotIn(search.normalized(child),
                         [search.normalized(b.source.after) for b in filtered.bindings])

    def test_qualified_parent_is_eligible_without_becoming_a_reward(self):
        child = plan().bindings[0].source.after
        filtered = plan(LEGACY + (child,), eligible_parent_sha256={digest(child)})
        self.assertEqual(filtered.parent_program, recover_program(BEFORE, child))
        self.assertTrue(all(b.source.after_sha256 != digest(child) for b in filtered.bindings))
        self.assertTrue(all('reward' not in b.source.hypothesis for b in filtered.bindings))

    def test_later_failed_parent_cannot_displace_an_eligible_parent(self):
        first = plan().bindings[0].source.after
        second = plan(LEGACY + (first,)).bindings[0].source.after
        filtered = plan(LEGACY + (first, second), eligible_parent_sha256={digest(first)})
        self.assertEqual(filtered.parent_program, recover_program(BEFORE, first))
        self.assertTrue({b.source.after_sha256 for b in filtered.bindings}.isdisjoint(
            {digest(first), digest(second)}))

    def test_invalid_failed_source_is_retained_without_parent_recovery(self):
        invalid = BEFORE + b'\n    \\"not valid Python\n'
        filtered = build_plan(BEFORE, history_sources=LEGACY + (invalid,),
            consumed_sha256={digest(x) for x in LEGACY + (invalid,)},
            historical_ast_sha256={search.normalized(x) for x in LEGACY},
            history_sha256='a'*64, mechanism_sha256='b'*64,
            eligible_parent_sha256=set())
        self.assertEqual(filtered.parent_program, SEED)
        self.assertNotIn(digest(invalid), [b.source.after_sha256 for b in filtered.bindings])

    def test_eligibility_does_not_reset_exhausted_seed_neighborhood(self):
        sources = LEGACY
        for _ in range(20):
            current = plan(sources, eligible_parent_sha256=set())
            if current is None:
                break
            self.assertEqual(current.parent_program, SEED)
            sources += tuple(b.source.after for b in current.bindings)
        else:
            self.fail('bounded seed neighborhood did not exhaust')
        self.assertIsNone(plan(sources, eligible_parent_sha256=set()))
        self.assertGreater(len(sources), len(LEGACY))

    def test_invalid_eligibility_cannot_silently_use_historical_parent_order(self):
        for value in ([], ['a'*64], True, {'wrong'}, {1}):
            with self.subTest(value=value), self.assertRaisesRegex(
                    ProgramRejected, 'PARENT_ELIGIBILITY'):
                plan(eligible_parent_sha256=value)


class OriginalOutcomeProjectionTests(unittest.TestCase):
    def setUp(self):
        self.fixture = owner_fixtures.ModelFreeOwnerPublicationTests(
            'test_exhausted_search_is_read_only_and_never_calls_provider')
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.db = self.fixture.db
        self.child = plan().bindings[0].source.after

    def event(self, ticket, source=None):
        intent = {'lane':'Yggdrasil', 'path':search.PATH,
                  'after_base64':base64.b64encode(source or self.child).decode('ascii')}
        return {'ticket':ticket, 'native_intent_base64':base64.b64encode(
            canonical(intent)).decode('ascii')}

    def project(self, events):
        with patch.object(search, 'native_events', return_value=events):
            return search.consumed_source_identities(
                self.db, set(), with_sources=True, with_parent_eligibility=True)

    def test_verified_task_is_read_only_eligible_with_complete_consumed_identity(self):
        ticket = self.db.conn.execute(
            "SELECT ticket FROM tasks WHERE stage='VERIFIED' LIMIT 1").fetchone()['ticket']
        head = self.db.meta().copy()
        raw, asts, sources, eligible = self.project([self.event(ticket)])
        self.assertEqual(eligible, {digest(self.child)})
        self.assertEqual(sources, (self.child,))
        self.assertIn(search.normalized(self.child), asts)
        self.assertEqual(self.db.meta(), head)

    def test_ready_then_quarantined_task_never_becomes_a_parent(self):
        from f139.nci04_owner_ledger import admit_native_issue
        native = self.fixture.fixture.fixture.native
        admit_native_issue(self.db, native, '2026-11-01T22:00:00Z')
        event = self.event(native.ticket)
        self.assertEqual(self.project([event])[3], set())
        self.db.claim(native.ticket, '2026-11-01T22:01:00Z')
        self.assertEqual(self.project([event])[3], set())
        self.db.quarantine(native.ticket, 'EXP_UNSUCCESSFUL')
        head = self.db.meta().copy()
        self.assertEqual(self.project([event])[3], set())
        verified = self.db.conn.execute(
            "SELECT ticket FROM tasks WHERE stage='VERIFIED' LIMIT 1").fetchone()['ticket']
        # An older PASS with identical bytes cannot override a retained failure.
        self.assertEqual(self.project([self.event(verified), event])[3], set())
        self.assertEqual(self.db.meta(), head)
        self.db.verify()

    def test_missing_task_fails_closed_and_cannot_consume_or_publish(self):
        head = self.db.meta().copy()
        with self.assertRaisesRegex(ValueError, 'PARENT_TASK_DRIFT'):
            self.project([self.event('missing-negative')])
        self.assertEqual(self.db.meta(), head)
        self.assertEqual(self.fixture.owner.write_calls, [])

    def test_parent_projection_requires_sources_and_verified_ledger(self):
        with self.assertRaisesRegex(ValueError, 'PARENT_SOURCES_REQUIRED'):
            search.consumed_source_identities(self.db, set(), with_parent_eligibility=True)
        with patch.object(self.db, 'verify', side_effect=ValueError('corrupt history')):
            with self.assertRaisesRegex(ValueError, 'corrupt history'):
                self.project([])


class LiveAdapterFeedbackTests(unittest.TestCase):
    def test_original_adapter_always_passes_explicit_original_outcome_eligibility(self):
        f = backend_fixtures.TypedOriginalPublisherConnectionTests(
            'test_original_publisher_authenticates_typed_candidate_after_all_seven')
        f.setUp()
        self.addCleanup(f.doCleanups)
        from f139 import nci04_prompt_program as program
        with patch.object(search, 'owner_request', return_value=f.prepared), \
                patch.object(backend, 'executable_custody', return_value=(None,'c'*64)), \
                patch.object(backend, 'typed_generation_custody'), \
                patch.object(backend, 'invoke', side_effect=f.utility_fixture), \
                patch.object(program, 'build_plan', wraps=program.build_plan) as build:
            result = f.fixture.publish()
        self.assertEqual(result['disposition'], 'MODEL_DRAFT_AUTHENTICATED')
        self.assertEqual(build.call_args.kwargs['eligible_parent_sha256'], frozenset())
        self.assertEqual(result['model_calls'], 0)
        f.db.verify()
