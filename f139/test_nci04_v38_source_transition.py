"""V38 diagnostic-source successor: frozen negative and fail-closed tests.

Synthetic fixtures do not authorize a live owner installation.
"""
import inspect
import json
import unittest
from unittest.mock import patch

from f139 import nci04_v37_source_transition as predecessor
from f139 import nci04_v38_source_transition as contract
from f139 import nci04_v38_original_owner_transition_cli as cli
from f139 import nci04_v32_original_owner_transition_cli as shared
from f139.local_controller import Database


class V38SuccessorTests(unittest.TestCase):
    def growing_history(self, pairs=7):
        from f139 import test_nci04_v37_source_transition as fixture_module
        from f139 import nci04_partial_publication_custody as custody
        fixture = fixture_module.V37ContractTests(
            'test_full_terminal_history_and_exact_negative_are_preserved')
        self.addCleanup(fixture.doCleanups)
        db, _ = fixture.history()
        seal = fixture_module.proof()
        seal['to_source_sha'] = contract.FROM_V37
        previous = fixture.previous() + [seal]
        db.conn.execute('INSERT INTO events VALUES(?,?,?,?,?)',
            (1240, 'SOURCE_TRANSITION_ADMITTED', 'd'*64, custody.EVENT, json.dumps(seal)))
        db.conn.execute('INSERT INTO events VALUES(?,?,?,?,?)',
            (1241, 'NATIVE_DEVELOPMENT_ACTIVATED', 'a'*64, 'd'*64, '{}'))
        for index in range(pairs):
            identity = format(10000 + index, '064x')
            attempt = {**custody.original_payload(), 'candidate_identity': identity,
                'source_after_sha256': identity, 'source_sha': contract.FROM_V37,
                'branch': 'f139/auto-model-y-' + identity[:20] + '-992ef142aaa5'}
            success = dict(schema=custody.PUBLICATION, candidate_identity=identity,
                source_after_sha256=identity, pr_number=900+index, head_commit='b'*40,
                scientific_first_use=False, worker_dispatched=False)
            for seq, kind, payload in (
                (1242+2*index, 'MODEL_DRAFT_ATTEMPTED', attempt),
                (1243+2*index, 'MODEL_DRAFT_AUTHENTICATED', success)):
                db.conn.execute('INSERT INTO events VALUES(?,?,?,?,?)',
                    (seq, kind, 'a'*64, 'a'*64, json.dumps(payload)))
            db.conn.execute('INSERT INTO tasks VALUES(?,?,?,?,?,?,?,?,?,?)',
                ('grown-positive-%02d'%index, 'VERIFIED', 2000+index, 'a'*64,
                 '/fixture-only', contract.FROM_V37, 'Yggdrasil', None, None, None))
        for seq in range(1242+2*pairs, 1305):
            db.conn.execute('INSERT INTO events VALUES(?,?,?,?,?)',
                            (seq, 'FIXTURE', 'a'*64, 'a'*64, '{}'))
        return db, dict(seq=1305, prior_sha='a'*64), previous

    def test_frozen_negative_and_grown_prefix_survive_full_cold_validation(self):
        from f139 import nci04_partial_publication_custody as custody
        for pairs in (0, 7):
            with self.subTest(pairs=pairs):
                db, row, previous = self.growing_history(pairs)
                with patch.object(contract, 'g54_original_canonical',
                                  return_value={'ticket':'fixture-g54'}):
                    state = contract.snapshot(db, row, previous)
                    self.assertEqual(state['partial_publication_custody'], custody.custody_packet())
                    self.assertEqual(state['verified_historical_tasks'], 89+pairs)
                    self.assertEqual(state['custodied_negative_tasks'], 56)
                    self.assertEqual(state['preserved_counters']['MODEL_DRAFT_ATTEMPTED'], 102+pairs)
                    self.assertEqual(state['preserved_counters']['MODEL_DRAFT_AUTHENTICATED'], 101+pairs)
                    doc = {**self.proof(), **state, 'original_head_seq':1304,
                           'prior_event_head_sha256':row['prior_sha']}
                    contract.verify_cold_event(db, row, doc, previous)
                self.assertEqual(custody.validate_original(db,1240),custody.custody_packet())
                if pairs:
                    # Reproduces the former bug: frozen102/101 cannot describe
                    # the current109/108 prefix. Neither counter is reset.
                    with self.assertRaises(custody.PartialPublicationDenied):
                        custody.validate_original(db,row['seq'])

    def test_growth_never_retires_unknown_or_replays_original_scope(self):
        from f139 import nci04_partial_publication_custody as custody
        db, row, previous = self.growing_history()
        attempt = json.loads(db.conn.execute('SELECT payload FROM events WHERE seq=1242').fetchone()[0])
        success = json.loads(db.conn.execute('SELECT payload FROM events WHERE seq=1243').fetchone()[0])
        cases = (
            ('unresolved', "DELETE FROM events WHERE seq=1243", ()),
            ('source drift', 'UPDATE events SET payload=? WHERE seq=1242',
             (json.dumps({**attempt,'source_sha':'f'*40}),)),
            ('duplicate identity', 'UPDATE events SET payload=? WHERE seq=1242',
             (json.dumps({**attempt,'candidate_identity':format(9,'064x')}),)),
            ('mismatched success', 'UPDATE events SET payload=? WHERE seq=1243',
             (json.dumps({**success,'source_after_sha256':'f'*64}),)),
            ('original anchor drift', "UPDATE events SET sha='bad' WHERE seq=1239", ()),
        )
        for name, statement, args in cases:
            with self.subTest(name=name):
                db.conn.execute('SAVEPOINT negative')
                db.conn.execute(statement,args)
                with patch.object(contract,'g54_original_canonical',return_value={'ticket':'fixture-g54'}):
                    with self.assertRaises(contract.MaintenanceDenied):
                        contract.snapshot(db,row,previous)
                db.conn.execute('ROLLBACK TO negative');db.conn.execute('RELEASE negative')
        db.conn.execute('SAVEPOINT hash_replay')
        for seq, doc in ((1242,attempt),(1243,success)):
            db.conn.execute('UPDATE events SET payload=? WHERE seq=?',
                (json.dumps({**doc,'source_after_sha256':custody.AFTER}),seq))
        with patch.object(contract,'g54_original_canonical',return_value={'ticket':'fixture-g54'}):
            with self.assertRaises(contract.MaintenanceDenied):contract.snapshot(db,row,previous)
        db.conn.execute('ROLLBACK TO hash_replay');db.conn.execute('RELEASE hash_replay')
        # Equal net counts cannot exchange the old negative for a new one.
        db.conn.execute('DELETE FROM events WHERE seq IN (1303,1304)')
        unknown = {**attempt,'candidate_identity':'e'*64,'source_after_sha256':'d'*64}
        false_success = {**success,'candidate_identity':custody.IDENTITY,'source_after_sha256':custody.AFTER}
        for seq,kind,doc in ((1303,'MODEL_DRAFT_ATTEMPTED',unknown),
                             (1304,'MODEL_DRAFT_AUTHENTICATED',false_success)):
            db.conn.execute('INSERT INTO events VALUES(?,?,?,?,?)',(seq,kind,'a'*64,'a'*64,json.dumps(doc)))
        with patch.object(contract,'g54_original_canonical',return_value={'ticket':'fixture-g54'}):
            with self.assertRaises(contract.MaintenanceDenied):contract.snapshot(db,row,previous)

    def previous(self):
        return [{"schema": predecessor.SCHEMA,
                 "from_source_sha": predecessor.FROM_V36,
                 "to_source_sha": contract.FROM_V37}]

    def proof(self):
        from f139.test_nci04_v37_source_transition import proof as v37_proof
        document = v37_proof(1241)
        document["schema"] = contract.SCHEMA
        document["from_source_sha"] = contract.FROM_V37
        document["to_source_sha"] = "e" * 40
        document["original_head_seq"] = 1241
        document["v37_transition_sha256"] = document.pop("v36_transition_sha256")
        document["purpose"] = "terminal-read-diagnostics"
        return document

    def test_schema_is_new_and_bound_to_exact_original_v37(self):
        self.assertEqual(contract.SCHEMA, "forge.f139.source-transition.v33")
        self.assertEqual(contract.FROM_V37,
                         "3dd63467d649a347692b6b42cd5074ff1038d3de")
        self.assertEqual(cli.contract, contract)
        self.assertIn("v38", inspect.getsource(shared.guarded_transition))
        self.assertNotEqual(contract.FIELDS, predecessor.FIELDS)

    def test_cold_proof_requires_purpose_and_immutable_negative_custody(self):
        doc = self.proof()
        row = {"seq": 1242, "prior_sha": doc["prior_event_head_sha256"]}
        from f139.nci04_native_contract import canonical
        state_keys = (
            "verified_historical_tasks", "custodied_negative_tasks",
            "custodied_negative_tickets", "terminal_tasks_sha256",
            "history_sha256", "v37_transition_sha256",
            "preserved_counters", "i1464_negative_event_sha256",
            "i1464_original_receipt_sha256", "partial_publication_custody")
        with patch.object(contract, "snapshot",
                          return_value={k: doc[k] for k in state_keys}):
            contract.verify_cold_event(None, row, doc, self.previous())
            for delta in (
                {"purpose": "model-execution"},
                {"schema": predecessor.SCHEMA},
                {"from_source_sha": predecessor.FROM_V36},
                {"to_source_sha": contract.FROM_V37},
                {"original_head_seq": 1240},
                {"original_head_seq": True},
                {"scientific_first_use": True},
                {"new_dispatches": 1},
                {"v2_receipt_authorized": True},
                {"preserved_counters": {}},
                {"i1464_negative_event_sha256": "0" * 64},
                {"partial_publication_custody": {}},
                {"v37_transition_sha256": "0" * 64},
                {"extra": True},
            ):
                with self.subTest(delta=delta), self.assertRaises(
                        contract.MaintenanceDenied):
                    contract.verify_cold_event(
                        None, row, {**doc, **delta}, self.previous())
            for chain in ([], self.previous() + [self.previous()[-1]],
                          [{"schema": "forge.f139.source-transition.v31",
                            "to_source_sha": contract.FROM_V37}]):
                with self.subTest(chain=chain), self.assertRaises(
                        contract.MaintenanceDenied):
                    contract.verify_cold_event(None, row, doc, chain)

    def test_spent_counters_preserve_the_single_original_partial_attempt(self):
        base = dict(G3_DRAFT_ATTEMPTED=1, G3_DRAFT_AUTHENTICATED=1,
                    FREE_REASONER_ATTEMPTED=8, MODEL_DRAFT_ATTEMPTED=102,
                    MODEL_DRAFT_AUTHENTICATED=101)
        self.assertTrue(contract.preserved_counters_valid(base))
        self.assertTrue(contract.preserved_counters_valid({
            **base, "MODEL_DRAFT_ATTEMPTED": 105,
            "MODEL_DRAFT_AUTHENTICATED": 104}))
        for delta in (
            {"MODEL_DRAFT_ATTEMPTED": 101},
            {"MODEL_DRAFT_ATTEMPTED": 103},
            {"MODEL_DRAFT_AUTHENTICATED": 102},
            {"FREE_REASONER_ATTEMPTED": 7},
            {"G3_DRAFT_ATTEMPTED": True},
            {"unknown": 1},
        ):
            with self.subTest(delta=delta):
                self.assertFalse(contract.preserved_counters_valid({
                    **base, **delta}))

    def test_no_write_or_read_without_original_custody(self):
        with self.assertRaises(contract.MaintenanceDenied):
            contract.build_proof(None, "e" * 40, 1, "a" * 64,
                                 contract.TOOLCHAIN)
        with self.assertRaises(contract.MaintenanceDenied):
            contract.readonly_snapshot(None)
        with self.assertRaises(contract.MaintenanceDenied):
            contract.commit_transition(None, {}, owner_witness=lambda: True)


class V38ReleaseGuardTests(unittest.TestCase):
    def git_fixture(self, *args):
        from f139 import check_v38_release_source as guard
        if args == ("rev-parse", "HEAD"):
            return "e" * 40
        if args[0] == "status":
            return ""
        if args[0] == "merge-base":
            return guard.BASELINE
        if args[0] == "diff":
            return "\n".join(sorted(guard.PATHS))
        raise AssertionError(args)

    def test_unique_v38_release_and_frozen_v37_route(self):
        from pathlib import Path
        from f139 import check_v38_release_source as guard
        root = Path(__file__).resolve().parents[1]
        self.assertEqual(guard.verify(root, get=self.git_fixture), "e" * 40)
        historical = (root / ".github/workflows/f139-v37-original-owner-release.yml").read_text()
        self.assertIn("&& github.sha == '3dd63467d649a347692b6b42cd5074ff1038d3de'",
                      historical)

    def test_drift_in_branch_source_or_manifest_fails_closed(self):
        from pathlib import Path
        from f139 import check_v38_release_source as guard
        root = Path(__file__).resolve().parents[1]
        for field in ("status", "merge-base", "diff"):
            def bad(*args):
                if args[0] == field:
                    if field == "status":
                        return "DIRTY"
                    if field == "merge-base":
                        return "0" * 40
                    return self.git_fixture(*args) + "\nf139/nci04_worker_v2.py"
                return self.git_fixture(*args)
            with self.subTest(field=field), self.assertRaises(ValueError):
                guard.verify(root, get=bad)


if __name__ == "__main__":
    unittest.main()
