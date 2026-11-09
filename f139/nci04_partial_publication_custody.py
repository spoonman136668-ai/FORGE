"""Exact original draft1239 negative custody; never a publication retry or success.

Only a cold-validated V37 original-owner source seal can retire this one pending
publication. Every attempt/hash stays consumed. Unknown pending writes stay held.
"""
import base64
import json
import re

from f139.nci04_native_contract import canonical, digest

SOURCE = '4f241d64ce8d9b2d8636eab56f5cc436c5d3b0ca'
SEQ = 1239
EVENT = '15e2a0ae74a663bc74810631f062176ad444b5aed36b96202e9eb91ab7ca2281'
PRIOR = 'a320780cafdc79dac7ffec1ed833550ee86a89c0207c78be6ee9821b99e4e05e'
IDENTITY = 'ac6038aaacf5b6f52d75a441f5ac607ed4f34469500cf02b0e25bdf8be894d36'
AFTER = 'f41672810fc6b7d391d26aa7bfc72a1b16b89fd65b9f5cefb0fb5681bd94cdcd'
PARENT = '992ef142aaa551156749a1de484a971b9a0c092f'
BRANCH = 'f139/auto-model-y-ac6038aaacf5b6f52d75-992ef142aaa5'
COMMIT = '573ae83f8a0f2f58b23f69c13c07a39a92a70aeb'
TREE = '5b9d6b779a891f43d2ae1c76c3d10cfc04959586'
BLOB = '84118840e3a3e8dfef0b0a148c565885b74671c3'
PATH = 'yggdrasil/public_causal_cells.py'
REPO = 'spoonman136668-ai/Yggdrasil'
TRANSITION = 'forge.f139.source-transition.v32'
PUBLICATION = 'forge.f139.owner-model-draft-publication.v1'


class PartialPublicationDenied(ValueError):
    pass


def need(ok, reason):
    if not ok:
        raise PartialPublicationDenied('F139_PARTIAL_DRAFT_' + reason)


def original_payload():
    return dict(schema=PUBLICATION, candidate_identity=IDENTITY,
        source_after_sha256=AFTER, source_sha=SOURCE, parent_commit=PARENT,
        branch=BRANCH, prior_event_head_sha256=PRIOR,
        scientific_first_use=False, retry_allowed=False)


def custody_packet():
    return dict(schema='forge.f139.partial-publication-negative.v1',
        original_event_seq=SEQ, original_event_sha256=EVENT,
        original_event_prior_sha256=PRIOR, original_attempt=original_payload(),
        repository=REPO, path=PATH, partial_commit=COMMIT, partial_tree=TREE,
        partial_blob=BLOB, source_after_sha256=AFTER,
        classification='PARTIAL_PUBLICATION_NO_PR', authenticated_success=False,
        original_diagnostic_run=42089011945, original_diagnostic_job=127461766428,
        remote_writes=0, retry_authorized=False, worker_dispatched=False,
        scientific_first_use=False)


def validate_original(db, boundary):
    """Offline exact-prefix validation, also used during cold source replay."""
    need(type(boundary) is int and boundary > SEQ, 'PREFIX_BOUNDARY')
    row = db.conn.execute('SELECT seq,kind,payload,prior_sha,sha FROM events WHERE seq=?',
                          (SEQ,)).fetchone()
    need(row is not None and row['kind']=='MODEL_DRAFT_ATTEMPTED'
        and row['sha']==EVENT and row['prior_sha']==PRIOR
        and json.loads(row['payload'])==original_payload(), 'ORIGINAL_ANCHOR_DRIFT')
    attempts, successes = _publication_prefix(db, boundary)
    need(len(attempts)==102 and len(successes)==101
        and set(attempts)-set(successes)=={IDENTITY}, 'EXACT_UNRESOLVED_HISTORY_REQUIRED')
    need(sum(v.get('source_after_sha256')==AFTER for v in attempts.values())==1,
         'SOURCE_REUSE_OR_DUPLICATE')
    return custody_packet()


def _publication_prefix(db, boundary):
    """Pure prefix parser: no db.verify recursion, authority or remote calls."""
    attempts, successes = {}, {}
    for event in db.conn.execute("SELECT seq,kind,payload FROM events WHERE kind IN "
            "('MODEL_DRAFT_ATTEMPTED','MODEL_DRAFT_AUTHENTICATED') AND seq<? ORDER BY seq",
            (boundary,)):
        doc = json.loads(event['payload'])
        need(type(doc) is dict, 'PUBLICATION_HISTORY_IDENTITY')
        key = doc.get('candidate_identity')
        need(type(doc) is dict and doc.get('schema')==PUBLICATION and isinstance(key,str)
            and re.fullmatch('[a-f0-9]{64}',key) and doc.get('scientific_first_use') is False,
            'PUBLICATION_HISTORY_IDENTITY')
        if event['kind']=='MODEL_DRAFT_ATTEMPTED':
            need(key not in attempts and doc.get('retry_allowed') is False,
                 'DUPLICATE_OR_REPLAYABLE_ATTEMPT')
            attempts[key] = doc
        else:
            need(key in attempts and key not in successes
                and doc.get('source_after_sha256')==attempts[key].get('source_after_sha256')
                and type(doc.get('pr_number')) is int and doc['pr_number']>0
                and isinstance(doc.get('head_commit'),str)
                and re.fullmatch('[a-f0-9]{40}',doc['head_commit'])
                and doc.get('worker_dispatched') is False, 'AUTHENTICATED_HISTORY_DRIFT')
            successes[key] = doc
    return attempts, successes


def validate_retained(db, boundary, frozen_boundary, source_sha, *,
                      successor_boundary=None, successor_source=None,
                      second_successor_boundary=None, second_successor_source=None):
    """Keep the exact V37 negative while permitting fully authenticated growth.

    Frozen 102/101 counts belong to the original V37 seal, never the growing
    current head. Every later attempt must still resolve; no new negative is
    invented, no scope/hash becomes replayable, and no counter is reset.
    """
    need(type(boundary) is int and type(frozen_boundary) is int
         and boundary >= frozen_boundary, 'GROWTH_BOUNDARY')
    need((successor_boundary is None and successor_source is None) or
         (type(successor_boundary) is int and frozen_boundary < successor_boundary < boundary
          and isinstance(successor_source, str) and re.fullmatch('[a-f0-9]{40}', successor_source)
          and successor_source != source_sha), 'SUCCESSOR_EPOCH_BOUNDARY')
    # Only the actual installed third epoch. Legacy one/two-epoch calls retain
    # their original semantics and cannot accept 42c70d74 growth implicitly.
    need((second_successor_boundary is None and second_successor_source is None) or
         (type(second_successor_boundary) is int and type(successor_boundary) is int
          and successor_boundary < second_successor_boundary < boundary
          and source_sha == '3dd63467d649a347692b6b42cd5074ff1038d3de'
          and successor_source == '54d556c3fdf1023d650f76c48ffb1bdc5ccc9135'
          and second_successor_source == '42c70d74dd93ef90d0f4618fefefe2206b81eafe'),
         'SECOND_SUCCESSOR_EPOCH_BOUNDARY')
    packet = validate_original(db, frozen_boundary)
    attempts, successes = _publication_prefix(db, boundary)
    need(len(attempts) >= 102 and len(successes) >= 101
         and set(attempts)-set(successes)=={IDENTITY}, 'UNRESOLVED_GROWTH')
    hashes = [v.get('source_after_sha256') for v in attempts.values()]
    need(all(isinstance(h, str) and re.fullmatch('[a-f0-9]{64}', h) for h in hashes)
         and len(set(hashes)) == len(hashes) and hashes.count(AFTER) == 1,
         'SOURCE_REUSE_OR_DUPLICATE')
    for row in db.conn.execute("SELECT seq,kind,payload FROM events WHERE kind IN "
            "('MODEL_DRAFT_ATTEMPTED','MODEL_DRAFT_AUTHENTICATED') AND seq>=? AND seq<? ORDER BY seq",
            (frozen_boundary, boundary)):
        doc = json.loads(row['payload'])
        if row['kind']=='MODEL_DRAFT_ATTEMPTED':
            expected_source = (successor_source if successor_boundary is not None
                               and row['seq'] >= successor_boundary else source_sha)
            if second_successor_boundary is not None and row['seq'] >= second_successor_boundary:
                expected_source = second_successor_source
            need(set(doc)==set(original_payload()) and doc['source_sha']==expected_source
                 and isinstance(doc['branch'], str)
                 and re.fullmatch(r'f139/auto-model-[wy]-[a-f0-9]{20}-[a-f0-9]{12}', doc['branch'])
                 and isinstance(doc['parent_commit'], str)
                 and re.fullmatch('[a-f0-9]{40}', doc['parent_commit'])
                 and isinstance(doc['prior_event_head_sha256'], str)
                 and re.fullmatch('[a-f0-9]{64}', doc['prior_event_head_sha256']),
                 'GROWTH_ATTEMPT_DRIFT')
        else:
            need(set(doc)=={'schema','candidate_identity','source_after_sha256',
                 'pr_number','head_commit','scientific_first_use','worker_dispatched'},
                 'GROWTH_SUCCESS_DRIFT')
    return packet


def verify_remote_readback(get):
    """Bounded GET-only confirmation; never creates or completes a PR."""
    need(callable(get), 'READ_PROVIDER_REQUIRED')
    prefix='repos/'+REPO+'/'
    def branch():
        doc=get(prefix+'git/ref/heads/'+BRANCH)
        need(type(doc) is dict and doc.get('ref')=='refs/heads/'+BRANCH
            and doc.get('object',{}).get('sha')==COMMIT, 'REMOTE_BRANCH_DRIFT')
    def no_pr():
        rows=get(prefix+'pulls?state=all&head=spoonman136668-ai:'+BRANCH+'&per_page=100')
        need(type(rows) is list and not rows, 'REMOTE_PR_PRESENT_OR_UNVERIFIED')
    branch()
    commit=get(prefix+'commits/'+COMMIT)
    need(type(commit) is dict and commit.get('sha')==COMMIT
        and commit.get('author',{}).get('login')=='spoonman136668-ai'
        and commit.get('committer',{}).get('login')=='spoonman136668-ai'
        and [p.get('sha') for p in commit.get('parents',[])]==[PARENT]
        and commit.get('commit',{}).get('tree',{}).get('sha')==TREE,
        'REMOTE_COMMIT_IDENTITY')
    delta=get(prefix+'compare/'+PARENT+'...'+COMMIT)
    files=delta.get('files') if type(delta) is dict else None
    need(type(delta) is dict and delta.get('status')=='ahead'
        and delta.get('ahead_by')==1 and delta.get('behind_by')==0
        and delta.get('total_commits')==1 and type(files) is list and len(files)==1
        and files[0].get('filename')==PATH and files[0].get('status')=='modified'
        and files[0].get('sha')==BLOB, 'REMOTE_ONE_FILE_DELTA')
    content=get(prefix+'contents/'+PATH+'?ref='+COMMIT)
    need(type(content) is dict and content.get('sha')==BLOB
        and content.get('encoding')=='base64' and isinstance(content.get('content'),str)
        and len(content['content'])<=100000, 'REMOTE_SOURCE_ENCODING')
    raw=base64.b64decode(''.join(content['content'].split()),validate=True)
    import hashlib
    need(digest(raw)==AFTER and hashlib.sha1(
        b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==BLOB, 'REMOTE_SOURCE_HASH')
    no_pr(); branch(); no_pr()
    return custody_packet()


def custodied_ids(db):
    """A prospective GET or packet alone grants nothing; require the real seal."""
    db.verify()
    rows=[]
    for row in db.conn.execute("SELECT seq,payload FROM events "
            "WHERE kind='SOURCE_TRANSITION_ADMITTED' ORDER BY seq"):
        doc=json.loads(row['payload'])
        if doc.get('schema')==TRANSITION: rows.append((row,doc))
    if not rows: return frozenset()
    need(len(rows)==1, 'DUPLICATE_SOURCE_SEAL')
    row,doc=rows[0]
    from f139.nci04_v37_source_transition import FIELDS
    need(set(doc)==FIELDS and doc['from_source_sha']==SOURCE
        and doc['partial_publication_custody']==custody_packet()
        and row['seq']==doc['original_head_seq']+1, 'SOURCE_SEAL_CUSTODY_DRIFT')
    validate_original(db,row['seq'])
    return frozenset({IDENTITY})
