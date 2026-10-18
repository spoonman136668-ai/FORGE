"""F139 inert D1 source contract: atomic append-only journal and strict no-replay."""
import json
import sqlite3
import unittest
from pathlib import Path
SQL = Path(__file__).with_name('d1.sql').read_text(encoding='utf-8')
ZERO = '0'*64
class D1Tests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(':memory:')
        self.db.executescript(SQL)
    def tearDown(self):
        self.db.close()
    def test_schema_starts_inert_with_zero_jobs(self):
        row = self.db.execute('SELECT revision,event_hash,state_json FROM f139_controller').fetchone()
        self.assertEqual((row[0],row[1]),(0,ZERO))
        self.assertEqual(json.loads(row[2])['stage'],'IDLE')
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM f139_tasks').fetchone()[0],0)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM f139_events').fetchone()[0],0)
    def test_cas_winner_has_exact_append_only_event(self):
        state=json.loads(self.db.execute('SELECT state_json FROM f139_controller').fetchone()[0])
        state['version']=1
        state['stage']='START_RISK'
        state['last_hash']='a'*64
        self.db.execute('UPDATE f139_controller SET revision=?,state_json=?,event_hash=?,event_kind=?,previous_hash=? WHERE id=1 AND revision=? AND event_hash=?',
            (1,json.dumps(state),'a'*64,'START_RISK',ZERO,0,ZERO))
        rows=self.db.execute('SELECT revision,event_hash,event_kind,previous_hash,state_json FROM f139_events').fetchall()
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0][:4],(1,'a'*64,'START_RISK',ZERO))
        self.assertEqual(rows[0][4],json.dumps(state))
        stale=self.db.execute('UPDATE f139_controller SET revision=2 WHERE id=1 AND revision=0')
        self.assertEqual(stale.rowcount,0)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM f139_events').fetchone()[0],1)
    def test_event_and_completion_cannot_be_removed_or_rewritten(self):
        self.db.execute("INSERT INTO f139_tasks(ticket,lane,source_sha) VALUES('f139-demo-001','Wingless',?)", ('a'*40,))
        self.db.execute("INSERT INTO f139_completed(ticket,run_id,source_sha) VALUES('f139-demo-001',42,?)", ('a'*40,))
        self.db.execute("UPDATE f139_controller SET revision=1,event_hash=?,event_kind='START_RISK',previous_hash=? WHERE id=1", ('a'*64,ZERO))
        for sql in ("DELETE FROM f139_events", "UPDATE f139_events SET event_hash='c'",
                    "DELETE FROM f139_completed", "UPDATE f139_completed SET run_id=43"):
            with self.subTest(sql=sql),self.assertRaises(sqlite3.IntegrityError):
                self.db.execute(sql)
    def test_completion_exactly_once_and_unique_run_id(self):
        source='b'*40
        for label in ('f139-demo-001','f139-demo-002'):
            self.db.execute('INSERT INTO f139_tasks(ticket,lane,source_sha) VALUES(?,?,?)',(label,'Wingless',source))
        self.db.execute('INSERT OR IGNORE INTO f139_completed(ticket,run_id,source_sha) VALUES(?,?,?)',('f139-demo-001',10,source))
        self.db.execute('INSERT OR IGNORE INTO f139_completed(ticket,run_id,source_sha) VALUES(?,?,?)',('f139-demo-001',10,source))
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM f139_completed').fetchone()[0],1)
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute('INSERT INTO f139_completed(ticket,run_id,source_sha) VALUES(?,?,?)',('f139-demo-002',10,source))
    def test_unauthorized_or_extra_lane_denied_by_store(self):
        for lane in ('Arbitrary','Production','Broker'):
            with self.subTest(lane=lane),self.assertRaises(sqlite3.IntegrityError):
                self.db.execute('INSERT INTO f139_tasks(ticket,lane,source_sha) VALUES(?,?,?)',
                    ('f139-demo-001',lane,'c'*40))
if __name__=='__main__':unittest.main()
