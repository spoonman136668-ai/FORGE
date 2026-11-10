"""Frozen event1462 ref-only negative; no publication retry or owner mutation."""
import base64
import hashlib
import json

from f139.nci04_native_contract import digest
from f139.nci04_partial_publication_custody import (
    IDENTITY as FIRST_IDENTITY, PUBLICATION, PartialPublicationDenied, _publication_prefix)

SOURCE = '42c70d74dd93ef90d0f4618fefefe2206b81eafe'
SEQ = 1462
EVENT = '2e7dd68acd559ebb468ce8e3797e31383f2ab40d805c3c8f988cfc68852f41a5'
PRIOR = 'b3052aba819fd71c625d0da7aa6af748f5b25343e70c4321c8ce36954bc61826'
IDENTITY = 'd10b72728b312111ba88c0cfd891dc992a974bc927edbd279430772f8dd3ca27'
AFTER = 'cbc542b8b4db78e3cba07cb3b438bc0833c4a3bda785430f23fa5a28d102ede6'
PARENT = '992ef142aaa551156749a1de484a971b9a0c092f'
BRANCH = 'f139/auto-model-y-d10b72728b312111ba88-992ef142aaa5'
REPO = 'spoonman136668-ai/Yggdrasil'
PATH = 'yggdrasil/public_causal_cells.py'
PARENT_BLOB = 'f2fda603fbed965a3b4e7cc28844b2246bf8ac2b'
PARENT_SHA256 = '4f57fef8f6e287ffef66ca8cf313cce5c137d76de9aba63201eb0401d1782c50'


def need(ok, reason):
    if not ok:
        raise PartialPublicationDenied('F139_REF_ONLY_1462_' + reason)


def original_payload():
    return dict(schema=PUBLICATION, candidate_identity=IDENTITY,
        source_after_sha256=AFTER, source_sha=SOURCE, parent_commit=PARENT,
        branch=BRANCH, prior_event_head_sha256=PRIOR,
        scientific_first_use=False, retry_allowed=False)


def custody_packet():
    return dict(schema='forge.f139.ref-only-publication-negative.v1',
        original_event_seq=SEQ, original_event_sha256=EVENT,
        original_event_prior_sha256=PRIOR, original_attempt=original_payload(),
        repository=REPO, path=PATH, branch_head=PARENT, original_parent_blob=PARENT_BLOB,
        original_parent_sha256=PARENT_SHA256, source_after_sha256=AFTER,
        classification='REF_ONLY_AT_UNCHANGED_PARENT_NO_PR',
        original_diagnostic_run=42725094500, original_diagnostic_job=129528719041,
        authenticated_success=False, remote_writes=0, retry_authorized=False,
        worker_dispatched=False, scientific_first_use=False)


def validate_original(db, boundary):
    # Exactly the witnessed head, never a general extra-negative exemption.
    need(type(boundary) is int and boundary == SEQ + 1, 'EXACT_PREFIX_BOUNDARY')
    row = db.conn.execute('SELECT seq,kind,payload,prior_sha,sha FROM events WHERE seq=?',
                          (SEQ,)).fetchone()
    need(row is not None and row['kind'] == 'MODEL_DRAFT_ATTEMPTED'
         and row['sha'] == EVENT and row['prior_sha'] == PRIOR
         and json.loads(row['payload']) == original_payload(), 'ORIGINAL_ANCHOR_DRIFT')
    prior = db.conn.execute('SELECT sha FROM events WHERE seq=?', (SEQ-1,)).fetchone()
    need(prior is not None and prior['sha'] == PRIOR, 'ORIGINAL_PREDECESSOR_DRIFT')
    attempts, successes = _publication_prefix(db, boundary)
    need(len(attempts) == 127 and len(successes) == 125
         and set(attempts)-set(successes) == {FIRST_IDENTITY, IDENTITY},
         'EXACT_UNRESOLVED_HISTORY_REQUIRED')
    need(sum(doc.get('source_after_sha256') == AFTER for doc in attempts.values()) == 1,
         'SOURCE_REUSE_OR_DUPLICATE')
    return custody_packet()


def verify_remote_readback(get):
    """GET-only negative readback; never complete, remove or retry a write."""
    need(callable(get), 'READ_PROVIDER_REQUIRED')
    prefix = 'repos/' + REPO + '/'
    def branch():
        doc = get(prefix+'git/ref/heads/'+BRANCH)
        need(type(doc) is dict and doc.get('ref') == 'refs/heads/'+BRANCH
             and type(doc.get('object')) is dict
             and doc['object'].get('type') == 'commit'
             and doc['object'].get('sha') == PARENT, 'REMOTE_BRANCH_DRIFT')
    def no_pr():
        rows = get(prefix+'pulls?state=all&head=spoonman136668-ai:'+BRANCH+'&per_page=100')
        need(type(rows) is list and not rows, 'REMOTE_PR_PRESENT_OR_UNVERIFIED')
    branch(); no_pr()
    content = get(prefix+'contents/'+PATH+'?ref='+PARENT)
    need(type(content) is dict and content.get('sha') == PARENT_BLOB
         and content.get('encoding') == 'base64' and isinstance(content.get('content'), str)
         and len(content['content']) <= 100000, 'REMOTE_SOURCE_ENCODING')
    try:
        raw = base64.b64decode(''.join(content['content'].split()), validate=True)
    except (ValueError, TypeError) as exc:
        raise PartialPublicationDenied('F139_REF_ONLY_1462_REMOTE_SOURCE_ENCODING') from exc
    need(digest(raw) == PARENT_SHA256 and digest(raw) != AFTER
         and hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest() == PARENT_BLOB,
         'REMOTE_SOURCE_HASH')
    no_pr(); branch(); no_pr()
    return custody_packet()
