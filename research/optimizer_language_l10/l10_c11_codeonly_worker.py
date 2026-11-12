#!/usr/bin/env python3
"""L10-C11 code-only artifact worker: source-free development demonstration.

Accept one bounded JSON input on stdin and produce one bounded JSON result.
Never accesses or imports L10 source/oracle modules or protected cohorts.
This is NOT an untrusted-code sandbox or authorized scientific evaluator.
"""
from __future__ import annotations
import json
import re
import sys

SCHEMA = 'forge.l10.c11.public-artifact-request-v1'
_ENTITY = re.compile(r'[A-Z][A-Za-z0-9_]{0,63}\Z')
_CODE = re.compile(r'P[0-9]{1,2}\Z')
_PREDICATE = re.compile(r'[a-z][a-z_]{1,31}\Z')


def _valid_observation(item):
    return (type(item) is list and len(item) == 4
            and type(item[0]) is str and _ENTITY.fullmatch(item[0])
            and type(item[1]) is str and _CODE.fullmatch(item[1])
            and type(item[2]) is str and _ENTITY.fullmatch(item[2])
            and item[0] != item[2]
            and type(item[3]) is int and item[3] in (-1, 1))


def predict(request):
    if type(request) is not dict or set(request) != {'schema', 'information_regime', 'observed', 'public_lexicon'}:
        raise ValueError('invalid envelope')
    if request['schema'] != SCHEMA or request['information_regime'] not in ('KNOWN_MAPPING', 'WITHHELD_MAPPING'):
        raise ValueError('unqualified regime')
    obs = request['observed']; lex = request['public_lexicon']
    if type(obs) is not list or not 0 < len(obs) <= 12 or not all(_valid_observation(x) for x in obs):
        raise ValueError('invalid observations')
    if type(lex) is not list or len(lex) > 12 or not all(type(x) is list and len(x) == 2
        and type(x[0]) is str and _CODE.fullmatch(x[0])
        and type(x[1]) is str and _PREDICATE.fullmatch(x[1]) for x in lex):
        raise ValueError('invalid lexicon')
    if request['information_regime'] == 'WITHHELD_MAPPING':
        if lex: raise ValueError('hidden regime cannot include lexicon')
        return {'status':'ABSTAIN', 'text':None, 'scientific_go':False}
    mapping = dict(lex)
    if len(mapping) != len(lex) or len(set(mapping.values())) != len(lex):
        raise ValueError('ambiguous mapping')
    if any(x[1] not in mapping for x in obs):
        return {'status':'ABSTAIN', 'text':None, 'scientific_go':False}
    text='; '.join(f'{sub} :: {mapping[code]} :: {obj} :: {"+" if pol==1 else "-"}'
                   for sub,code,obj,pol in obs)
    return {'status':'DEVELOPMENT_ONLY', 'text':text, 'scientific_go':False}


def main():
    raw=sys.stdin.buffer.read(16385)
    if len(raw) > 16384:
        raise ValueError('oversize input')
    response=predict(json.loads(raw))
    encoded=(json.dumps(response,sort_keys=True,separators=(',', ':'))+'\n').encode('utf-8')
    if len(encoded)>4096: raise ValueError('oversize output')
    sys.stdout.buffer.write(encoded)


if __name__ == '__main__':
    try:
        main()
    except (ValueError, json.JSONDecodeError):
        print('{"scientific_go":false,"status":"BLOCKED_INPUT"}')
        sys.exit(2)
