"""Exact witnessed ref-only failure controls; fixtures never prove live custody."""
import base64
from contextlib import closing
import copy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from f139 import nci04_ref_only_publication_custody as ref_only
from f139 import nci04_partial_publication_custody as original
from f139 import nci04_v40_source_transition as route
from f139 import test_nci04_v40_source_transition as prior_tests


class RefOnlyPublicationCustodyTests(unittest.TestCase):
    def history(self):
        fixture = prior_tests.V40SuccessorTests()
        self.addCleanup(fixture.doCleanups)
        db, row, previous = fixture.history()
        # Replace the final synthetic acknowledged pair by the actual witnessed
        # pending identity at seq1462. Hash padding remains synthetic, not an
        # authentic owner/HMAC database or source acceptance witness.
        for seq in (1343, 1344):
            db.conn.execute("UPDATE events SET kind='FIXTURE_PREFIX_PADDING',payload='{}' WHERE seq=?", (seq,))
        db.conn.execute('UPDATE events SET sha=? WHERE seq=1461', (ref_only.PRIOR,))
        db.conn.execute('UPDATE events SET kind=?,sha=?,prior_sha=?,payload=? WHERE seq=1462',
            ('MODEL_DRAFT_ATTEMPTED', ref_only.EVENT, ref_only.PRIOR,
             json.dumps(ref_only.original_payload())))
        row['prior_sha'] = ref_only.EVENT
        return fixture, db, row, previous

    def test_exact_pair_preserves_failure_counters_without_success_or_write(self):
        fixture, db, row, previous = self.history()
        before = db.conn.total_changes
        state = fixture.snapshot(db, row, previous)
        self.assertEqual(state['preserved_counters']['MODEL_DRAFT_ATTEMPTED'], 127)
        self.assertEqual(state['preserved_counters']['MODEL_DRAFT_AUTHENTICATED'], 125)
        packet = state['partial_publication_custody']
        self.assertEqual(packet, dict(schema='forge.f139.partial-publication-pair.v1',
            original_negative=original.custody_packet(), ref_only_negative=ref_only.custody_packet()))
        proof = {**fixture.document(state), 'prior_event_head_sha256': ref_only.EVENT}
        with patch.object(route, 'g54_original_canonical', return_value={'ticket':'fixture-g54'}):
            route.verify_cold_event(db, row, proof, previous)
            corrupt = copy.deepcopy(proof)
            corrupt['partial_publication_custody']['ref_only_negative']['authenticated_success'] = True
            with self.assertRaises(route.MaintenanceDenied):
                route.verify_cold_event(db, row, corrupt, previous)
        self.assertEqual(db.conn.total_changes, before)
        with self.assertRaises(original.PartialPublicationDenied):
            original.validate_retained(db, row['seq'], 1240,
                '3dd63467d649a347692b6b42cd5074ff1038d3de',
                successor_boundary=1305, successor_source='54d556c3fdf1023d650f76c48ffb1bdc5ccc9135',
                second_successor_boundary=1309, second_successor_source=ref_only.SOURCE)

    def test_wrong_event_payload_hash_predecessor_or_replay_fails_closed(self):
        _, db, row, _ = self.history()
        for field, value in (('branch','f139/other'), ('candidate_identity','e'*64),
                             ('source_after_sha256','e'*64), ('parent_commit','e'*40),
                             ('retry_allowed',True), ('scientific_first_use',True)):
            db.conn.execute('SAVEPOINT fault')
            db.conn.execute('UPDATE events SET payload=? WHERE seq=1462',
                (json.dumps({**ref_only.original_payload(),field:value}),))
            with self.subTest(field=field), self.assertRaises(original.PartialPublicationDenied):
                ref_only.validate_original(db, row['seq'])
            db.conn.execute('ROLLBACK TO fault'); db.conn.execute('RELEASE fault')
        for statement in ("UPDATE events SET sha='wrong' WHERE seq=1462",
                          "UPDATE events SET prior_sha='wrong' WHERE seq=1462",
                          "UPDATE events SET sha='wrong' WHERE seq=1461",
                          "DELETE FROM events WHERE seq=1462"):
            db.conn.execute('SAVEPOINT fault'); db.conn.execute(statement)
            with self.subTest(statement=statement), self.assertRaises(original.PartialPublicationDenied):
                ref_only.validate_original(db, row['seq'])
            db.conn.execute('ROLLBACK TO fault'); db.conn.execute('RELEASE fault')
        for boundary in (1462, 1464, True):
            with self.subTest(boundary=boundary), self.assertRaises(original.PartialPublicationDenied):
                ref_only.validate_original(db, boundary)

    def reads(self):
        raw = (Path(__file__).parent/'fixtures/model_free_yggdrasil_992ef.py').read_bytes()
        prefix = 'repos/'+ref_only.REPO+'/'
        return {
            prefix+'git/ref/heads/'+ref_only.BRANCH: dict(ref='refs/heads/'+ref_only.BRANCH,
                object=dict(type='commit',sha=ref_only.PARENT)),
            prefix+'pulls?state=all&head=spoonman136668-ai:'+ref_only.BRANCH+'&per_page=100': [],
            prefix+'contents/'+ref_only.PATH+'?ref='+ref_only.PARENT:
                dict(sha=ref_only.PARENT_BLOB,encoding='base64',content=base64.b64encode(raw).decode()),
        }

    def test_get_only_remote_witness_checks_parent_bytes_no_pr_and_repeat_drift(self):
        reads, calls = self.reads(), []
        def get(path):
            calls.append(path)
            return reads[path]
        self.assertEqual(ref_only.verify_remote_readback(get),ref_only.custody_packet())
        self.assertEqual(len(calls),6)
        self.assertTrue(all(path.startswith('repos/'+ref_only.REPO+'/') for path in calls))
        for path in reads:
            altered = copy.deepcopy(reads)
            if '/git/ref/' in path:
                altered[path]['object']['sha'] = 'f'*40
            elif '/pulls?' in path:
                altered[path] = [dict(number=123)]
            else:
                altered[path]['content'] = base64.b64encode(b'changed source').decode()
            with self.subTest(path=path), self.assertRaises(original.PartialPublicationDenied):
                ref_only.verify_remote_readback(lambda p: altered[p])
        count = 0
        def drift(path):
            nonlocal count
            count += 1
            if count == 5:
                return dict(ref='refs/heads/'+ref_only.BRANCH,object=dict(type='commit',sha='f'*40))
            return reads[path]
        with self.assertRaises(original.PartialPublicationDenied):
            ref_only.verify_remote_readback(drift)
        def unavailable(path):
            raise ValueError('provider unavailable')
        with self.assertRaises(ValueError):
            ref_only.verify_remote_readback(unavailable)

    def test_new_identity_is_not_retired_until_exact_cold_valid_source_seal(self):
        fixture, db, row, previous = self.history()
        # Isolate the seal parser only. Fixture padding cannot pass real db.verify.
        with patch.object(db, 'verify', create=True):
            self.assertEqual(original.custodied_ids(db),frozenset({original.IDENTITY}))
            state = fixture.snapshot(db,row,previous)
            proof = {**fixture.document(state),'prior_event_head_sha256':ref_only.EVENT}
            db.conn.execute('INSERT INTO events VALUES(?,?,?,?,?)',
                (1463,'SOURCE_TRANSITION_ADMITTED','b'*64,ref_only.EVENT,json.dumps(proof)))
            self.assertEqual(original.custodied_ids(db),frozenset({original.IDENTITY,ref_only.IDENTITY}))
            proof['partial_publication_custody']['ref_only_negative']['retry_authorized'] = True
            db.conn.execute('UPDATE events SET payload=? WHERE seq=1463',(json.dumps(proof),))
            with self.assertRaises(original.PartialPublicationDenied):
                original.custodied_ids(db)

    def test_native_additional_witness_requires_original_anchor_and_provider(self):
        _,db,row,_=self.history()
        with patch.object(db,'meta',return_value={'head_seq':1462},create=True):
            route.verify_additional_publication_readback(db,lambda p:self.reads()[p])
            with patch.object(ref_only,'verify_remote_readback',side_effect=original.PartialPublicationDenied('drift')):
                with self.assertRaises(route.MaintenanceDenied):
                    route.verify_additional_publication_readback(db,lambda p:None)
        counts=dict(G3_DRAFT_ATTEMPTED=1,G3_DRAFT_AUTHENTICATED=1,FREE_REASONER_ATTEMPTED=8,
                    MODEL_DRAFT_ATTEMPTED=127,MODEL_DRAFT_AUTHENTICATED=125)
        self.assertTrue(route.preserved_counters_valid(counts))
        for update in ({'FREE_REASONER_ATTEMPTED':7},{'MODEL_DRAFT_AUTHENTICATED':124},
                       {'MODEL_DRAFT_ATTEMPTED':128,'MODEL_DRAFT_AUTHENTICATED':126}):
            self.assertFalse(route.preserved_counters_valid({**counts,**update}))

if __name__ == '__main__':
    unittest.main()
