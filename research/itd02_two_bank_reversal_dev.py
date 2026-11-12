"""ITD-02 two-bank numerical consequence learning. Synthetic DEV only.

Uses public observations and *delivered* action consequences, no environment,
first-use, worker or authority APIs. Protocol ancestor 6548cc25d66034db4ac0a90263444ca090b6f319.
"""
import hashlib
import json
import math
import re
from itd02_online_consequence_memory import OnlineConsequenceMemory

SCHEMA = 'forge.eureka.itd02.two-bank-reversal-dev.v1'
PROTOCOL_COMMIT = '6548cc25d66034db4ac0a90263444ca090b6f319'
GENESIS = '0' * 64
SHA_RE = re.compile(r'^[0-9a-f]{64}$')
THRESHOLD = 0.9
MAX_CHECKPOINT_BYTES = 5000000


def canonical(obj):
    return json.dumps(obj,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')


def sha(payload):
    return hashlib.sha256(payload).hexdigest()


class TwoBankMemory:
    """Only observes completed interventions; never executes proposed actions."""
    def __init__(self, public_dim=2, actions=2, max_events=1000):
        if (type(public_dim) is not int or not 2<=public_dim<=6 or
            type(actions) is not int or not 2<=actions<=6 or
            type(max_events) is not int or not 1<=max_events<=10000):
            raise ValueError('ITD02_TWO_BANK_INVALID_CAPACITY')
        self.public_dim=public_dim
        self.actions=actions
        self.max_events=max_events
        self.banks=[OnlineConsequenceMemory(public_dim,actions,max_events) for _ in range(2)]
        self.active=0
        self.completed=0
        self.head=GENESIS
        self.events=[]
        self.pending=[]
        self.unresolved=0

    def _valid(self,seq,observation,action,consequence):
        if type(seq) is not int or seq!=self.completed or seq>=self.max_events:
            raise ValueError('ITD02_TWO_BANK_EVENT_SEQUENCE_INVALID')
        if type(observation) not in (list,tuple) or len(observation)!=self.public_dim:
            raise ValueError('ITD02_TWO_BANK_PUBLIC_INPUT_INVALID')
        values=[]
        for x in observation:
            if type(x) not in (int,float) or not math.isfinite(x) or not -1<=x<=1:
                raise ValueError('ITD02_TWO_BANK_PUBLIC_INPUT_INVALID')
            values.append(float(x))
        if type(action) is not int or not 0<=action<self.actions:
            raise ValueError('ITD02_TWO_BANK_INVALID_ACTION')
        if type(consequence) not in (int,float) or not math.isfinite(consequence) or not -100<=consequence<=100:
            raise ValueError('ITD02_TWO_BANK_INVALID_CONSEQUENCE')
        return {'seq':seq,'obs':values,'action':action,'consequence':float(consequence)}

    def _update(self,bank,event):
        m=self.banks[bank]
        m.observe(m.completed,event['obs'],event['action'],event['consequence'])

    def observe(self,event_seq,observation,action,consequence):
        e=self._valid(event_seq,observation,action,consequence)
        active=self.banks[self.active]
        alternate=self.banks[1-self.active]
        mature=active.counts[action]>=3
        wrong=(mature and abs(active.predict(e['obs'],action)-e['consequence'])>=THRESHOLD)
        if not wrong:
            # A lone noisy contradiction is not sufficient to create a mode.
            for old in self.pending:
                self._update(self.active,old)
            self.pending.clear()
            self._update(self.active,e)
        else:
            inactive_mature=alternate.counts[action]>=3
            alt_error=(abs(alternate.predict(e['obs'],action)-e['consequence'])
                       if inactive_mature else math.inf)
            active_error=abs(active.predict(e['obs'],action)-e['consequence'])
            # A third never-seen regime must not be mistaken for a known one
            # merely because the known alternative is *less wrong*.
            alt_win=(inactive_mature and alt_error<THRESHOLD and
                     alt_error+THRESHOLD<=active_error)
            empty_alternate=alternate.completed==0
            kind=('return' if alt_win else 'new' if empty_alternate else 'uncertain')
            if self.pending and self.pending[0]['kind']!=kind:
                # Neither bank has supplied two coherent pieces of change evidence.
                self.unresolved+=len(self.pending)
                self.pending.clear()
            self.pending.append({**e,'kind':kind})
            if len(self.pending)>=2:
                if kind in ('return','new'):
                    target=1-self.active
                    for buffered in self.pending:
                        self._update(target,buffered)
                    self.active=target
                else:
                    self.unresolved+=len(self.pending)
                self.pending.clear()
        record={**e,'prev':self.head}
        self.head=sha(bytes.fromhex(self.head)+canonical(record))
        self.events.append(record)
        self.completed+=1

    def propose(self,observation,exploration_weight=0.):
        out=self.banks[self.active].propose(observation,exploration_weight)
        return {**out,'selected_bank':self.active,'pending_contradictions':len(self.pending),
                'unresolved_observations':self.unresolved,'wrapper_seen':self.completed,
                'can_dispatch_original':False,'scientific_accepted':False}

    def checkpoint(self):
        banks=[]
        for b in self.banks:
            payload,digest=b.checkpoint()
            banks.append({'payload':payload.decode('utf-8'),'sha256':digest})
        obj={'schema':SCHEMA,'protocol_commit':PROTOCOL_COMMIT,
             'public_dim':self.public_dim,'actions':self.actions,
             'max_events':self.max_events,'completed':self.completed,
             'active':self.active,'pending':self.pending,'unresolved':self.unresolved,
             'head':self.head,'events':self.events,'banks':banks,
             'original_first_use_authorized':False,'scientific_accepted':False}
        raw=canonical(obj)
        if len(raw)>MAX_CHECKPOINT_BYTES:
            raise ValueError('ITD02_TWO_BANK_CHECKPOINT_TOO_LARGE')
        return raw,sha(raw)

    @classmethod
    def restore(cls,payload,expected_sha256,minimum_completed=0):
        if (type(payload) is not bytes or len(payload)>MAX_CHECKPOINT_BYTES or
            type(expected_sha256) is not str or not SHA_RE.fullmatch(expected_sha256) or
            sha(payload)!=expected_sha256 or type(minimum_completed) is not int or
            minimum_completed<0):
            raise ValueError('ITD02_TWO_BANK_EXTERNAL_DIGEST_OR_FLOOR_INVALID')
        def unique(items):
            out={}
            for k,v in items:
                if k in out: raise ValueError('ITD02_TWO_BANK_DUPLICATE_JSON_KEY')
                out[k]=v
            return out
        try:
            x=json.loads(payload.decode('utf-8'),object_pairs_hook=unique,
                         parse_constant=lambda _:(_ for _ in ()).throw(ValueError('NONFINITE')))
        except (UnicodeError,ValueError) as exc:
            raise ValueError('ITD02_TWO_BANK_MALFORMED_JSON') from exc
        fields={'schema','protocol_commit','public_dim','actions','max_events',
                'completed','active','pending','unresolved','head','events','banks',
                'original_first_use_authorized','scientific_accepted'}
        if (type(x) is not dict or set(x)!=fields or x['schema']!=SCHEMA or
            x['protocol_commit']!=PROTOCOL_COMMIT or canonical(x)!=payload or
            x['original_first_use_authorized'] is not False or
            x['scientific_accepted'] is not False):
            raise ValueError('ITD02_TWO_BANK_PROTOCOL_OR_SCHEMA_DRIFT')
        out=cls(x['public_dim'],x['actions'],x['max_events'])
        if (type(x['completed']) is not int or
            not minimum_completed<=x['completed']<=out.max_events or
            type(x['active']) is not int or x['active'] not in (0,1) or
            type(x['unresolved']) is not int or x['unresolved']<0 or
            type(x['events']) is not list or len(x['events'])!=x['completed'] or
            type(x['pending']) is not list or len(x['pending'])>1 or
            type(x['banks']) is not list or len(x['banks'])!=2):
            raise ValueError('ITD02_TWO_BANK_HISTORY_OR_DIMENSIONS_INVALID')
        h=GENESIS
        for i,rec in enumerate(x['events']):
            if (type(rec) is not dict or set(rec)!={'seq','obs','action','consequence','prev'} or
                rec['prev']!=h):
                raise ValueError('ITD02_TWO_BANK_BROKEN_EVENT_CHAIN')
            out.completed=i
            out._valid(rec['seq'],rec['obs'],rec['action'],rec['consequence'])
            h=sha(bytes.fromhex(h)+canonical(rec))
        if h!=x['head']:
            raise ValueError('ITD02_TWO_BANK_HEAD_MISMATCH')
        if any(type(p) is not dict or set(p)!={'seq','obs','action','consequence','kind'} or
               p['kind'] not in ('return','new','uncertain') or
               type(p['seq']) is not int or p['seq']!=x['completed']-1 or
               p['obs']!=x['events'][-1]['obs'] or
               p['action']!=x['events'][-1]['action'] or
               p['consequence']!=x['events'][-1]['consequence'] for p in x['pending']):
            raise ValueError('ITD02_TWO_BANK_PENDING_INVALID')
        restored=[]
        for b in x['banks']:
            if type(b) is not dict or set(b)!={'payload','sha256'} or type(b['payload']) is not str:
                raise ValueError('ITD02_TWO_BANK_BANK_FORMAT_INVALID')
            restored.append(OnlineConsequenceMemory.restore(
                b['payload'].encode('utf-8'),b['sha256'],minimum_completed=0))
        if sum(m.completed for m in restored)+len(x['pending'])+x['unresolved']!=x['completed']:
            raise ValueError('ITD02_TWO_BANK_UNACCOUNTED_OBSERVATIONS')
        out.banks=restored
        out.events=x['events']
        out.pending=x['pending']
        out.head=x['head']
        out.completed=x['completed']
        out.active=x['active']
        out.unresolved=x['unresolved']
        return out
