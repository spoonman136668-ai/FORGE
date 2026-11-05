"""Falsify exact draft1239 reconciliation without original writes or publication."""
import base64
from contextlib import closing
import copy
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from f139 import nci04_partial_publication_custody as custody
from f139 import nci04_v37_source_transition as route
from f139 import test_nci04_v37_source_transition as fixtures
from f139 import nci04_model_owner_publication as publisher
from f139.local_controller import Database


class PartialPublicationTests(unittest.TestCase):
    def history(self):
        fixture=fixtures.V37ContractTests('test_full_terminal_history_and_exact_negative_are_preserved')
        fixture._cleanups=[]
        db,_=fixture.history()
        self.addCleanup(fixture.doCleanups)
        return db

    def test_exact_original_prefix_and_every_anchor_field(self):
        db=self.history()
        self.assertEqual(custody.validate_original(db,1240),custody.custody_packet())
        for sql in ("UPDATE events SET sha='wrong' WHERE seq=1239",
                    "UPDATE events SET prior_sha='wrong' WHERE seq=1239",
                    "UPDATE events SET kind='FIXTURE' WHERE seq=1239",
                    "DELETE FROM events WHERE seq=103"):
            with self.subTest(sql=sql):
                db.conn.execute('SAVEPOINT falsify');db.conn.execute(sql)
                with self.assertRaises(custody.PartialPublicationDenied):custody.validate_original(db,1240)
                db.conn.execute('ROLLBACK TO falsify');db.conn.execute('RELEASE falsify')
        for boundary in (True,1239,0):
            with self.assertRaises(custody.PartialPublicationDenied):custody.validate_original(db,boundary)
        for key,value in (('source_sha','e'*40),('retry_allowed',True),
                ('candidate_identity','f'*64),('scientific_first_use',True)):
            payload={**custody.original_payload(),key:value}
            db.conn.execute('SAVEPOINT falsify')
            db.conn.execute('UPDATE events SET payload=? WHERE seq=1239',(json.dumps(payload),))
            with self.assertRaises(custody.PartialPublicationDenied):custody.validate_original(db,1240)
            db.conn.execute('ROLLBACK TO falsify');db.conn.execute('RELEASE falsify')

    def test_no_false_success_or_different_unresolved_scope(self):
        db=self.history()
        for delta in ({'candidate_identity':custody.IDENTITY}, {'source_after_sha256':'e'*64}):
            db.conn.execute('SAVEPOINT falsify')
            row=db.conn.execute('SELECT payload FROM events WHERE seq=110').fetchone()
            doc={**json.loads(row['payload']),**delta}
            db.conn.execute('UPDATE events SET payload=? WHERE seq=110',(json.dumps(doc),))
            with self.assertRaises(custody.PartialPublicationDenied):custody.validate_original(db,1240)
            db.conn.execute('ROLLBACK TO falsify');db.conn.execute('RELEASE falsify')

    def test_read_packet_or_unsealed_database_does_not_retire_a_scope(self):
        with tempfile.TemporaryDirectory() as temp,closing(Database.initialize(
                Path(temp)/'state.sqlite',custody.SOURCE)) as db:
            self.assertEqual(custody.custodied_ids(db),frozenset())
            self.assertFalse(custody.custody_packet()['authenticated_success'])
            self.assertFalse(custody.custody_packet()['retry_authorized'])
            before=db.meta().copy()
            with self.assertRaises(route.MaintenanceDenied):
                route.build_proof(db,'f'*40,42,'a'*64,route.TOOLCHAIN)
            self.assertEqual(db.meta(),before)

    def test_cold_verification_failure_never_returns_a_negative_witness(self):
        db=SimpleNamespace(verify=Mock(side_effect=ValueError('forged source seal')))
        with self.assertRaisesRegex(ValueError,'forged source seal'):custody.custodied_ids(db)

    def test_only_exact_cold_validated_source_seal_retires_the_one_identity(self):
        db=self.history();db.verify=Mock()
        proof=fixtures.proof()
        db.conn.execute('INSERT INTO events VALUES(?,?,?,?,?)',(1240,
            'SOURCE_TRANSITION_ADMITTED','d'*64,custody.EVENT,json.dumps(proof)))
        self.assertEqual(custody.custodied_ids(db),frozenset({custody.IDENTITY}))
        db.verify.assert_called_once()
        for delta in ({'from_source_sha':'e'*40}, {'original_head_seq':1238},
                {'partial_publication_custody':{}}, {'extra':False}):
            db.conn.execute('UPDATE events SET payload=? WHERE seq=1240',
                (json.dumps({**proof,**delta}),))
            with self.assertRaises(custody.PartialPublicationDenied):custody.custodied_ids(db)
        db.conn.execute('UPDATE events SET payload=? WHERE seq=1240',(json.dumps(proof),))
        db.conn.execute('INSERT INTO events VALUES(?,?,?,?,?)',(1241,
            'SOURCE_TRANSITION_ADMITTED','e'*64,'d'*64,json.dumps(proof)))
        with self.assertRaisesRegex(custody.PartialPublicationDenied,'DUPLICATE_SOURCE_SEAL'):
            custody.custodied_ids(db)

    def test_packet_is_copied_and_cannot_be_mutated_into_success(self):
        packet=custody.custody_packet();packet['original_attempt']['retry_allowed']=True
        self.assertFalse(custody.custody_packet()['original_attempt']['retry_allowed'])

    def test_remote_drift_and_existing_pr_fail_without_any_write(self):
        # Real frozen source bytes are separately SHA-bound, not executed.
        root='repos/'+custody.REPO+'/'
        branch=dict(ref='refs/heads/'+custody.BRANCH,object=dict(sha=custody.COMMIT))
        commit=dict(sha=custody.COMMIT,author=dict(login='spoonman136668-ai'),
            committer=dict(login='spoonman136668-ai'),parents=[dict(sha=custody.PARENT)],
            commit=dict(tree=dict(sha=custody.TREE)))
        delta=dict(status='ahead',ahead_by=1,behind_by=0,total_commits=1,
            files=[dict(filename=custody.PATH,status='modified',sha=custody.BLOB)])
        responses={root+'git/ref/heads/'+custody.BRANCH:branch,
            root+'commits/'+custody.COMMIT:commit,
            root+'compare/'+custody.PARENT+'...'+custody.COMMIT:delta,
            root+'contents/'+custody.PATH+'?ref='+custody.COMMIT:
                dict(sha=custody.BLOB,encoding='base64',content=base64.b64encode(b'fixture').decode()),
            root+'pulls?state=all&head=spoonman136668-ai:'+custody.BRANCH+'&per_page=100':[]}
        # Mock only cryptographic primitive outputs for this request-shape unit
        # fixture. Actual original-host preflight validates real public bytes.
        def get(path):return copy.deepcopy(responses[path])
        with patch.object(custody,'digest',return_value=custody.AFTER),\
             patch('hashlib.sha1',return_value=SimpleNamespace(hexdigest=lambda:custody.BLOB)):
            self.assertEqual(custody.verify_remote_readback(get),custody.custody_packet())
            for path,mutation in (
                (root+'git/ref/heads/'+custody.BRANCH,dict(ref='refs/heads/'+custody.BRANCH,object=dict(sha='f'*40))),
                (root+'commits/'+custody.COMMIT,{**commit,'author':dict(login='foreign')}),
                (root+'compare/'+custody.PARENT+'...'+custody.COMMIT,{**delta,'ahead_by':2}),
                (root+'pulls?state=all&head=spoonman136668-ai:'+custody.BRANCH+'&per_page=100',[dict(number=999)])):
                with self.subTest(path=path):
                    original=responses[path];responses[path]=mutation
                    with self.assertRaises(custody.PartialPublicationDenied):custody.verify_remote_readback(get)
                    responses[path]=original
        with self.assertRaises(custody.PartialPublicationDenied):custody.verify_remote_readback(get)

    def test_publication_replay_is_still_denied_and_unknown_holds_remain(self):
        # The real publication-history parser sees the complete synthetic journal;
        # only the cold-qualified witness is stubbed, never a successful draft.
        db=self.history()
        db.conn.execute('DELETE FROM events WHERE kind IN (\'MODEL_DRAFT_ATTEMPTED\',\'MODEL_DRAFT_AUTHENTICATED\')')
        payload=custody.original_payload()
        db.conn.execute('INSERT INTO events VALUES(?,?,?,?,?)',(1239,'MODEL_DRAFT_ATTEMPTED',
            custody.EVENT,custody.PRIOR,json.dumps(payload)))
        with patch.object(custody,'custodied_ids',return_value=frozenset({custody.IDENTITY})):
            publisher._publication_history(db,'e'*64,'d'*64)
            for identity,sha in ((custody.IDENTITY,'d'*64),('e'*64,custody.AFTER)):
                with self.assertRaisesRegex(publisher.ModelDraftDenied,'PREVIOUSLY_ATTEMPTED_NO_REPLAY'):
                    publisher._publication_history(db,identity,sha)
        with patch.object(custody,'custodied_ids',return_value=frozenset()):
            with self.assertRaisesRegex(publisher.ModelDraftDenied,'UNRESOLVED_REMOTE_WRITE'):
                publisher._publication_history(db,'e'*64,'d'*64)
        foreign={**payload,'candidate_identity':'b'*64,'source_after_sha256':'c'*64}
        db.conn.execute('INSERT INTO events VALUES(?,?,?,?,?)',(1240,'MODEL_DRAFT_ATTEMPTED',
            'a'*64,custody.EVENT,json.dumps(foreign)))
        with patch.object(custody,'custodied_ids',return_value=frozenset({custody.IDENTITY})):
            with self.assertRaisesRegex(publisher.ModelDraftDenied,'UNRESOLVED_REMOTE_WRITE'):
                publisher._publication_history(db,'e'*64,'d'*64)


if __name__=='__main__':unittest.main()
