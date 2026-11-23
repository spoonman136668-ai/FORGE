"""Private-fixture phase timing only; never changes controller or durability.

SQL text/parameters, paths and database contents are not retained. Python API
elapsed times include the call's work/waits, not independent fsync measurements.
Cursor fetches, SQLite internals, destructor closes and child processes are not
covered. Nested intercepted operations are counted only at the outer boundary.
"""
from contextlib import contextmanager
from pathlib import Path
import shutil
import sqlite3
import threading
import time
from unittest.mock import patch
from urllib.parse import urlsplit
from urllib.request import url2pathname


class PhaseRecorder:
    def __init__(self, root, *, enabled=True, clock=time.perf_counter):
        self.root=Path(root).resolve()
        self.enabled=enabled
        self.clock=clock
        self.rows={}
        self.bypasses=0
        self.threads=set()
        self.local=threading.local()
        self.lock=threading.Lock()

    def private(self, path):
        try:
            Path(path).resolve().relative_to(self.root)
            return True
        except (ValueError, TypeError):
            return False

    def database_allowed(self, name):
        value=str(name)
        if value==':memory:': return True
        if value.startswith('file:'):
            parsed=urlsplit(value)
            if parsed.netloc not in ('','localhost'): return False
            value=url2pathname(parsed.path)
        return self.private(value)

    def call(self, kind, function, *args, **kwargs):
        if not self.enabled or getattr(self.local,'depth',0):
            return function(*args,**kwargs)
        self.local.depth=1
        started=self.clock(); failed=True
        try:
            result=function(*args,**kwargs); failed=False
            return result
        finally:
            elapsed=self.clock()-started
            self.local.depth=0
            with self.lock:
                self.threads.add(threading.get_ident())
                row=self.rows.setdefault(kind,dict(calls=0,seconds=0.0,errors=0))
                row['calls']+=1; row['seconds']+=elapsed; row['errors']+=int(failed)

    def snapshot(self):
        with self.lock:
            return {kind:dict(row) for kind,row in self.rows.items()}


def verb(sql):
    token=str(sql).lstrip().split(None,1)[0].upper() if str(sql).strip() else ''
    return token if token in ('BEGIN','COMMIT','ROLLBACK','INSERT','UPDATE','DELETE','SELECT','PRAGMA','CREATE') else 'OTHER'


@contextmanager
def private_sqlite_probe(recorder):
    connect=sqlite3.connect
    copyfile,copy2=shutil.copyfile,shutil.copy2

    class TimedConnection(sqlite3.Connection):
        def execute(self, sql, *args, **kwargs):
            return recorder.call('sqlite_execute_'+verb(sql),super().execute,sql,*args,**kwargs)
        def executemany(self, sql, *args, **kwargs):
            return recorder.call('sqlite_executemany_'+verb(sql),super().executemany,sql,*args,**kwargs)
        def executescript(self, *args, **kwargs):
            return recorder.call('sqlite_script',super().executescript,*args,**kwargs)
        def commit(self): return recorder.call('sqlite_commit_method',super().commit)
        def rollback(self): return recorder.call('sqlite_rollback_method',super().rollback)
        def close(self): return recorder.call('sqlite_close',super().close)
        def backup(self, *args, **kwargs):
            return recorder.call('sqlite_backup',super().backup,*args,**kwargs)
        def __exit__(self, *args):
            return recorder.call('sqlite_context_exit',super().__exit__,*args)

    def guarded_connect(database, *args, **kwargs):
        if not recorder.database_allowed(database):
            raise ValueError('PHASE_PROBE_PRIVATE_DATABASE_REQUIRED')
        # Preserve explicitly supplied factories rather than replace semantics.
        if recorder.enabled:
            if len(args)>=5 or 'factory' in kwargs:
                recorder.bypasses+=1
            else:
                kwargs['factory']=TimedConnection
        return recorder.call('sqlite_connect',connect,database,*args,**kwargs)

    def copied(kind, original, source, target, *args, **kwargs):
        if recorder.private(source) and recorder.private(target):
            return recorder.call(kind,original,source,target,*args,**kwargs)
        if recorder.enabled: recorder.bypasses+=1
        return original(source,target,*args,**kwargs)

    with patch.object(sqlite3,'connect',guarded_connect), \
         patch.object(shutil,'copyfile',lambda *a,**k: copied('file_copy',copyfile,*a,**k)), \
         patch.object(shutil,'copy2',lambda *a,**k: copied('file_copy2',copy2,*a,**k)):
        yield
