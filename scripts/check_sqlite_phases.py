"""Private-fixture phase probe controls; outside original test discovery."""
import json
from pathlib import Path
import shutil
import sqlite3
import tempfile
import unittest
from f139.profile_sqlite_phases import PhaseRecorder,private_sqlite_probe


class PhaseControls(unittest.TestCase):
    def exercise(self, enabled):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); recorder=PhaseRecorder(root,enabled=enabled)
            with private_sqlite_probe(recorder):
                conn=sqlite3.connect(root/'state.sqlite',isolation_level=None)
                try:
                    conn.execute('PRAGMA journal_mode=WAL')
                    conn.execute('PRAGMA synchronous=FULL')
                    conn.execute('CREATE TABLE t (n INTEGER UNIQUE)')
                    conn.execute('BEGIN IMMEDIATE'); conn.execute('INSERT INTO t VALUES (1)'); conn.execute('COMMIT')
                    conn.execute('BEGIN IMMEDIATE'); conn.execute('INSERT INTO t VALUES (2)'); conn.execute('ROLLBACK')
                    with self.assertRaises(sqlite3.IntegrityError): conn.execute('INSERT INTO t VALUES (1)')
                    value=list(conn.execute('SELECT * FROM t'))
                    modes=(conn.execute('PRAGMA synchronous').fetchone()[0],conn.execute('PRAGMA journal_mode').fetchone()[0])
                    with conn: conn.execute('INSERT INTO t VALUES (3)')
                finally: conn.close()
                shutil.copy2(root/'state.sqlite',root/'copy.sqlite')
                copy=sqlite3.connect(root/'copy.sqlite')
                try: restored=list(copy.execute('SELECT * FROM t ORDER BY n'))
                finally: copy.close()
            return value,modes,restored,recorder.snapshot()

    def test_real_parity_rollback_cold_copy_and_error(self):
        plain=self.exercise(False); timed=self.exercise(True)
        self.assertEqual(plain[:3],timed[:3]); self.assertEqual(timed[1],(2,'wal'))
        self.assertEqual(timed[2],[(1,),(3,)])
        self.assertEqual(plain[3],{})
        for phase in ('sqlite_connect','sqlite_execute_COMMIT','sqlite_execute_ROLLBACK','sqlite_close','file_copy2'):
            self.assertGreater(timed[3][phase]['calls'],0)
        self.assertEqual(timed[3]['sqlite_execute_INSERT']['errors'],1)
        self.assertNotIn('file_copy',timed[3])  # copy2's nested copyfile not double-counted.

    def test_private_boundary_and_uri(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); r=PhaseRecorder(root)
            with private_sqlite_probe(r):
                with self.assertRaisesRegex(ValueError,'PRIVATE_DATABASE_REQUIRED'):
                    sqlite3.connect(root.parent/'outside.sqlite')
                path=root/'inside.sqlite'; c=sqlite3.connect(path); c.close()
                c=sqlite3.connect(path.as_uri()+'?mode=ro',uri=True); c.close()
            self.assertEqual(r.snapshot()['sqlite_connect']['calls'],2)

    def test_custom_factory_preserved_and_marked(self):
        with tempfile.TemporaryDirectory() as directory:
            r=PhaseRecorder(directory)
            class Custom(sqlite3.Connection): pass
            with private_sqlite_probe(r):
                c=sqlite3.connect(':memory:',factory=Custom)
                self.assertIs(type(c),Custom); c.close()
            self.assertEqual(r.bypasses,1)

    def test_nested_accounting_exception_and_restoration(self):
        ticks=iter([1.0,4.0]); r=PhaseRecorder('.',clock=lambda: next(ticks))
        original=sqlite3.connect
        with self.assertRaisesRegex(RuntimeError,'sentinel'):
            with private_sqlite_probe(r):
                def failing(): raise RuntimeError('sentinel')
                r.call('outer',lambda: r.call('inner',failing))
        self.assertIs(sqlite3.connect,original)
        self.assertEqual(r.snapshot(),dict(outer=dict(calls=1,seconds=3.0,errors=1)))

    def test_payloads_and_paths_never_recorded(self):
        result=self.exercise(True)[3]
        self.assertTrue(all(set(row)=={'calls','seconds','errors'} for row in result.values()))
        self.assertNotIn('state.sqlite',json.dumps(result))


if __name__=='__main__': unittest.main(verbosity=2)
