"""V39 source/custody falsification. Fixtures never grant live authority."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from f139 import nci04_v39_source_transition as route
from f139 import nci04_v38_source_transition as prior
from f139 import nci04_v39_original_owner_transition_cli as cli
from f139 import nci04_v38_original_owner_transition_cli as shared_cli
from f139 import nci04_partial_publication_custody as custody
from f139 import check_v39_release_source as guard
from f139.local_controller import Database, SingleOwner
from f139.nci04_native_contract import canonical
from f139 import test_nci04_v38_source_transition as prior_tests

ROOT = Path(__file__).resolve().parents[1]


class V39Tests(unittest.TestCase):
    def history(self):
        fixture = prior_tests.V38SuccessorTests('test_frozen_negative_and_grown_prefix_survive_full_cold_validation')
        self.addCleanup(fixture.doCleanups)
        db, _, previous = fixture.growing_history()
        with patch.object(prior, 'g54_original_canonical', return_value={'ticket':'fixture-g54'}):
            state = prior.snapshot(db, dict(seq=1305, prior_sha='a'*64), previous)
        v38 = {**fixture.proof(), **state, 'original_head_seq':1304,
               'to_source_sha':route.FROM_V38, 'prior_event_head_sha256':'a'*64}
        db.conn.execute('INSERT INTO events VALUES(?,?,?,?,?)',
                        (1305,'SOURCE_TRANSITION_ADMITTED','c'*64,'a'*64,json.dumps(v38)))
        db.conn.execute('INSERT INTO events VALUES(?,?,?,?,?)',
                        (1306,'NATIVE_DEVELOPMENT_ACTIVATED','a'*64,'c'*64,'{}'))
        identity = 'f'*64
        attempt = {**custody.original_payload(), 'candidate_identity':identity,
                   'source_after_sha256':identity, 'source_sha':route.FROM_V38,
                   'branch':'f139/auto-model-y-'+identity[:20]+'-992ef142aaa5'}
        success = dict(schema=custody.PUBLICATION,candidate_identity=identity,
            source_after_sha256=identity,pr_number=1001,head_commit='b'*40,
            scientific_first_use=False,worker_dispatched=False)
        for seq,kind,doc in ((1307,'MODEL_DRAFT_ATTEMPTED',attempt),
                             (1308,'MODEL_DRAFT_AUTHENTICATED',success)):
            db.conn.execute('INSERT INTO events VALUES(?,?,?,?,?)',
                            (seq,kind,'a'*64,'a'*64,json.dumps(doc)))
        db.conn.execute('INSERT INTO tasks VALUES(?,?,?,?,?,?,?,?,?,?)',
            ('v38-positive','VERIFIED',5000,'a'*64,'/fixture',route.FROM_V38,
             'Yggdrasil',None,None,None))
        return db, dict(seq=1309,prior_sha='a'*64), previous+[v38]

    def snapshot(self, db, row, previous):
        with patch.object(route,'g54_original_canonical',return_value={'ticket':'fixture-g54'}):
            return route.snapshot(db,row,previous)

    def document(self, state):
        return dict(schema=route.SCHEMA,from_source_sha=route.FROM_V38,to_source_sha='e'*40,
            owner_event_id=123,prior_event_head_sha256='a'*64,original_head_seq=1308,
            **state,genenv_executable_sha256='b'*64,genenv_toolchain=route.TOOLCHAIN,
            generation_mechanism_sha256='c'*64,new_dispatches=0,
            scientific_first_use=False,v2_receipt_authorized=False,
            purpose='public-rate-equivalence-preflight')

    def test_real_sqlite_two_epoch_prefix_and_all_negatives_are_preserved(self):
        db,row,previous=self.history()
        state=self.snapshot(db,row,previous)
        self.assertEqual(state['verified_historical_tasks'],97)
        self.assertEqual(state['custodied_negative_tasks'],56)
        self.assertEqual(state['preserved_counters']['MODEL_DRAFT_ATTEMPTED'],110)
        self.assertEqual(state['preserved_counters']['MODEL_DRAFT_AUTHENTICATED'],109)
        self.assertEqual(state['partial_publication_custody'],custody.custody_packet())
        self.assertEqual(state['v38_transition_sha256'],'c'*64)
        document=self.document(state)
        with patch.object(route,'g54_original_canonical',return_value={'ticket':'fixture-g54'}):
            route.verify_cold_event(db,row,document,previous)
        # Old one-epoch parsing must reject the source54d growth, not broaden itself.
        with self.assertRaises(custody.PartialPublicationDenied):
            custody.validate_retained(db,1309,1240,prior.FROM_V37)

    def test_wrong_epoch_missing_ack_source_reuse_and_negative_tamper_fail_closed(self):
        db,row,previous=self.history()
        attempt=json.loads(db.conn.execute('SELECT payload FROM events WHERE seq=1307').fetchone()[0])
        old=json.loads(db.conn.execute('SELECT payload FROM events WHERE seq=1242').fetchone()[0])
        mutations=(
            ('DELETE FROM events WHERE seq=1308',()),
            ('UPDATE events SET payload=? WHERE seq=1307',(json.dumps({**attempt,'source_sha':prior.FROM_V37}),)),
            ('UPDATE events SET payload=? WHERE seq=1242',(json.dumps({**old,'source_sha':route.FROM_V38}),)),
            ("UPDATE events SET sha='bad' WHERE seq=1239",()),
            ("UPDATE tasks SET stage='READY' WHERE ticket='v38-positive'",()),
            ("DELETE FROM tasks WHERE ticket=?",(route.I1464_TICKET,)),
            ("UPDATE events SET sha='bad' WHERE seq=1305",()),
        )
        for statement,args in mutations:
            with self.subTest(statement=statement):
                db.conn.execute('SAVEPOINT fault');db.conn.execute(statement,args)
                try:
                    state=self.snapshot(db,row,previous)
                    with patch.object(route,'g54_original_canonical',return_value={'ticket':'fixture-g54'}):
                        with self.assertRaises(route.MaintenanceDenied):
                            route.verify_cold_event(db,row,self.document({**state,'v38_transition_sha256':'c'*64}),previous)
                except route.MaintenanceDenied:
                    pass
                finally:
                    db.conn.execute('ROLLBACK TO fault');db.conn.execute('RELEASE fault')
        for kwargs in ({'successor_boundary':1305}, {'successor_source':route.FROM_V38},
                       {'successor_boundary':True,'successor_source':route.FROM_V38},
                       {'successor_boundary':1240,'successor_source':route.FROM_V38},
                       {'successor_boundary':1305,'successor_source':prior.FROM_V37}):
            with self.subTest(kwargs=kwargs),self.assertRaises(custody.PartialPublicationDenied):
                custody.validate_retained(db,1309,1240,prior.FROM_V37,**kwargs)

    def test_cold_event_rejects_authority_identity_and_spend_drift(self):
        db,row,previous=self.history();state=self.snapshot(db,row,previous);doc=self.document(state)
        for change in ({'schema':prior.SCHEMA},{'from_source_sha':prior.FROM_V37},
                       {'to_source_sha':route.FROM_V38},{'purpose':'terminal-read-diagnostics'},
                       {'scientific_first_use':True},{'new_dispatches':1},{'v2_receipt_authorized':True},
                       {'original_head_seq':True},{'owner_event_id':True},
                       {'history_sha256':'0'*64},{'v38_transition_sha256':'0'*64},
                       {'genenv_executable_sha256':'bad'},{'generation_mechanism_sha256':'bad'},
                       {'preserved_counters':{}},{'extra':False}):
            with self.subTest(change=change),patch.object(route,'snapshot',return_value=state):
                with self.assertRaises(route.MaintenanceDenied):
                    route.verify_cold_event(db,row,{**doc,**change},previous)
        for chain in ([],previous+[previous[-1]],previous+[doc],
                      [{**previous[-1],'from_source_sha':'0'*40}]):
            with self.subTest(chain=chain),self.assertRaises(route.MaintenanceDenied):
                route.verify_cold_event(db,row,doc,chain)

    def test_missing_original_and_postverify_failure_cannot_mutate(self):
        with tempfile.TemporaryDirectory() as td:
            db=Database.initialize(Path(td)/'state.sqlite', route.FROM_V38)
            self.addCleanup(db.close)
            before=db.meta().copy()
            with SingleOwner(db.filename.with_suffix('.lock')):
                with self.assertRaises(route.MaintenanceDenied):
                    route.build_proof(db,'e'*40,1,'b'*64,route.TOOLCHAIN)
                empty={k:None for k in route.FIELDS}
                empty['to_source_sha']='e'*40
                with patch.object(route,'build_proof',return_value=empty),patch.object(db,'verify',side_effect=ValueError('cold replay rejected')):
                    with self.assertRaisesRegex(ValueError,'cold replay rejected'):
                        route.commit_transition(db,empty,owner_witness=lambda:True)
            self.assertEqual(db.meta(),before);db.verify()
        with self.assertRaises(route.MaintenanceDenied):route.readonly_snapshot(None)
        with self.assertRaises(route.MaintenanceDenied):route.commit_transition(None,{},owner_witness=lambda:True)
        self.assertIs(shared_cli.selected_contract(route),route)
        with self.assertRaises(prior.MaintenanceDenied):shared_cli.selected_contract(object())
        with self.assertRaises(route.MaintenanceDenied):
            cli.main(['--db','unused','--target',route.FROM_V38,'--backup','unused','--verify-pretransition-rollback'])

    def test_v34_modern_guard_requires_complete_fields_and_original_custody(self):
        from f139.local_controller import v2_owner_terminal_release_guard
        db,row,previous=self.history();doc=self.document(self.snapshot(db,row,previous))
        with tempfile.TemporaryDirectory() as td:
            original=Database.initialize(Path(td)/'state.sqlite','e'*40)
            self.addCleanup(original.close)
            original.enable(legacy_suspended=True)
            original.event('SOURCE_TRANSITION_ADMITTED',doc)
            with patch.object(original,'verify'),patch('f139.local_controller.g54_original_canonical'), \
                    patch('f139.nci04_g49_prepost_negative.verify_g49_custody',return_value=True), \
                    patch('f139.nci04_owner_ledger.verify_native_activation',return_value=True):
                self.assertTrue(v2_owner_terminal_release_guard('e'*40,original))
                for change in ({'v2_receipt_authorized':True}, {'schema':'forge.f139.source-transition.v35'}):
                    original.event('SOURCE_TRANSITION_ADMITTED',{**doc,**change})
                    self.assertFalse(v2_owner_terminal_release_guard('e'*40,original))

    def git_fixture(self,*args):
        if args==('rev-parse','HEAD'):return 'e'*40
        if args[0]=='status':return ''
        if args==('merge-base',guard.FROM_V38,guard.BASELINE):return guard.FROM_V38
        if args[0]=='merge-base':return guard.BASELINE
        if args[:2]==('diff','--name-only'):return '' if '--' in args else '\n'.join(sorted(guard.PATHS))
        raise AssertionError(args)

    def test_exact_source_guard_denies_dirty_extra_path_filter_drift_or_wrong_ancestry(self):
        self.assertEqual(guard.verify(ROOT,get=self.git_fixture),'e'*40)
        for fault in ('status','diff','merge-base','filter'):
            def get(*args):
                if args[0]==fault:return 'dirty' if fault=='status' else '0'*40
                if fault=='filter' and args[0]=='diff' and '--' in args:return 'f139/nci04_prompt_program.py'
                return self.git_fixture(*args)
            with self.subTest(fault=fault),self.assertRaises(ValueError):guard.verify(ROOT,get=get)

    @unittest.skipUnless(os.name=='nt','actual Windows PowerShell parser')
    def test_full_successor_install_script_parses_without_running_owner_operations(self):
        source=(ROOT/'.github/workflows/f139-v38-original-owner-release.yml').read_text()
        segment=source.split('  install-v39:',1)[1].split('  recover-pretransition-v38:',1)[0].split('        run: |',1)[1]
        script='\n'.join(line[10:] for line in segment.splitlines() if line.startswith('          '))
        checker="$code=[Console]::In.ReadToEnd();$tokens=$null;$errors=$null;[void][System.Management.Automation.Language.Parser]::ParseInput($code,[ref]$tokens,[ref]$errors);if($errors.Count -gt 0){$errors | ForEach-Object {$_.Message};exit 1};exit 0"
        result=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',checker],input=script,text=True,capture_output=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    def test_prequiesce_rehearsal_and_production_controls_keep_order_and_no_competing_job(self):
        source=(ROOT/'.github/workflows/f139-v38-original-owner-release.yml').read_text()
        install=source.split('  install-v39:',1)[1].split('  recover-pretransition-v38:',1)[0]
        markers=['check_v39_release_source.py','--preflight-only --rehearse-copy',
                 'Disable-ScheduledTask','go build','ORIGINAL_COLD_CUSTODY_BUNDLE=PASS',
                 '--genenv-executable $genenv','POLICY_SOURCE_PROMOTION_FAILED','Enable-ScheduledTask']
        positions=[install.index(x) for x in markers];self.assertEqual(positions,sorted(positions))
        self.assertEqual(source.count('  install-v'),1)
        self.assertIn("$old='"+route.FROM_V38+"'",install)
        self.assertIn("$rule.bypass_actors",install)
        self.assertIn('F139_V39_POSTMUTATION_EXISTING_TASK_DISABLED_AND_QUIESCENT',install)


if __name__=='__main__':unittest.main()
