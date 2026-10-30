#!/usr/bin/env python3
"""NR-M1P: read-only authenticated original-source audit; no environment interaction."""
import argparse
from collections import Counter,defaultdict
import hashlib, json, math, re, zipfile

ZIP_SHA='25575d33723017be52ed57f014c6cea8baaa34bb9bc1616ad876f372d66b2a2c'
SOURCE_SHA='69dbc08751f65013874eec1c1e32c108fb51fb356820474b1702bf08bae6e019'
ROLES=('wingless_mg19_unchanged','yggdrasil_mg19_unchanged')
FAMILIES=('MiniGrid-KeyCorridorS3R2-v0','MiniGrid-KeyCorridorS4R3-v0','MiniGrid-ObstructedMaze-1Dl-v0')
COLORS={'red':0,'green':1,'blue':2,'purple':3,'yellow':4,'grey':5}
OBJECTS={'key':5,'ball':6,'box':7}
MISSION=re.compile(r'pick up the (red|green|blue|purple|yellow|grey) (key|ball|box)')

def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')
def digest(x):return hashlib.sha256(canonical(x)).hexdigest()
def sha(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for block in iter(lambda:f.read(4*1024*1024),b''):h.update(block)
    return h.hexdigest()

def public_key(p):
    if not isinstance(p,dict) or set(p)!={'image','direction','mission'}:raise ValueError('PUBLIC_SHAPE')
    if not isinstance(p['mission'],str) or not p['mission'] or not isinstance(p['direction'],int) or p['direction'] not in range(4):raise ValueError('PUBLIC_MISSION_HEADING')
    image=p['image']
    if (not isinstance(image,list) or len(image)!=7 or any(not isinstance(row,list) or len(row)!=7 or any(not isinstance(cell,list) or len(cell)!=3 or any(type(c)!=int for c in cell) for cell in row) for row in image)):raise ValueError('PUBLIC_IMAGE_SHAPE')
    front=image[3][5]
    return p['mission'],p['direction'],*front

def original_effects(e):
    b=e['before'];after=e['after'];action=e['action'];before_key=public_key(b);after_key=public_key(after)
    front=b['image'][3][5];aft=after['image'][3][5]
    same_heading=b['direction']==after['direction'];same_color=front[1]==aft[1]
    match=MISSION.fullmatch(b['mission'])
    first_visible=False;target_pickup=False
    if match:
        color,obj=match.groups();type_code=OBJECTS[obj];color_code=COLORS[color]
        def visible(p):return any(cell[0]==type_code and cell[1]==color_code for row in p['image'] for cell in row)
        first_visible=not visible(b) and visible(after)
        target_pickup=bool(action==3 and front[0]==type_code and front[1]==color_code and aft[0]==1 and same_heading)
    door_open=bool(action==5 and front[0]==aft[0]==4 and same_heading and same_color and front[2] in (1,2) and aft[2]==0)
    door_close=bool(action==5 and front[0]==aft[0]==4 and same_heading and same_color and front[2]==0 and aft[2]==1)
    terminal_reward=bool(e['reward']>0 and e['terminated'])
    return {'public_change':digest(b)!=digest(after),
            'turn_change':action in (0,1) and digest(b)!=digest(after),
            'forward_view_change':action==2 and digest(b)!=digest(after),
            'other_view_change':action not in (0,1,2) and digest(b)!=digest(after),
            'door_open':door_open,'door_close':door_close,
            'target_first_visible':first_visible,'target_pickup':target_pickup,
            'terminal_goal':terminal_reward,
            'strict_task_effect':door_open or target_pickup or terminal_reward}

def candidate_alternatives(row):
    """Union over all seven hypothetical parent choices, not actual MG28 proposals."""
    eligible={}
    for parent in range(7):
        count,changes,*rest=row[parent]
        prior=10000*(changes+1)//(count+2)
        best=-1;highest=0
        for action,item in enumerate(row):
            n,changed,*_=item
            if n<3:continue
            score=10000*(changed+1)//(n+2)
            if score>=7500 and score>=prior+1000 and score>highest:
                best=action;highest=score
        if best>=0 and best!=parent:eligible[parent]=best
    return eligible

def census(receipt):
    source=receipt['source']
    if (digest(source)!=SOURCE_SHA or receipt['canonical_source_sha256']!=SOURCE_SHA or
        len(source['original_234_episodes'])!=234 or source['scientific_first_use'] is not False or source['zero_external_actions'] is not True):raise ValueError('FROZEN_ORIGINAL_IDENTITY_DRIFT')
    episodes=source['original_234_episodes']
    rows=[]
    for role in ROLES:
        for family in FAMILIES:
            series=sorted([ep for ep in episodes if ep['role']==role and ep['family']==family],key=lambda ep:ep['seed_dev_exposed'])
            if len(series)!=3 or len({ep['seed_dev_exposed'] for ep in series})!=3:raise ValueError('FROZEN_ROLE_FAMILY_COHORT_DRIFT')
            # count,changed,door_open,door_close,target_first_visible,target_pickup,terminal_goal
            memory=defaultdict(lambda:[[0]*7 for _ in range(7)])
            c=Counter();by_action=defaultdict(Counter);positive=False
            for ep in series:
                evs=ep['source_events']
                if digest(evs)!=ep['source_events_sha256'] or len(evs)!=ep['original_source_actions'] or len(evs)>192:raise ValueError('FROZEN_SELECTED_ACTION_DIGEST_DRIFT')
                for index,e in enumerate(evs,1):
                    if (e['index']!=index or e['external_actions']!=0 or e['mission']!=ep['original_public_mission'] or
                        digest(e['before'])!=e['before_sha256'] or digest(e['after'])!=e['after_sha256'] or
                        e['before']['mission']!=e['after']['mission'] or e['before']['mission']!=e['mission']):raise ValueError('ORIGINAL_PUBLIC_OBSERVATION_TAMPER')
                    a=e['action'];r=e['reward']
                    if type(a)!=int or a not in range(7) or type(r) not in (float,int) or not math.isfinite(r) or not -1<=r<=1:raise ValueError('SOURCE_ACTION_REWARD')
                    k=public_key(e['before']);public_key(e['after']);row=memory[k]
                    supported=candidate_alternatives(row)  # BEFORE recording the same event
                    if supported:
                        alts=set(supported.values())
                        c['optimistic_support_all']+=1
                        if not positive:c['optimistic_support_pre_first_reward']+=1
                        c['turn_only_alternatives']+=int(alts.issubset({0,1}))
                        c['any_nonturn_alternatives']+=int(bool(alts-{0,1}))
                        c['source_selected_matches_supported_alt']+=int(a in alts)
                        relevant_actions={alt for alt in alts if any(row[alt][q] for q in (2,5,6))}
                        if relevant_actions:c['optimistic_support_prior_strict_task_effect']+=1
                        c['supported_alternatives_with_task_effect']+=len(relevant_actions)
                        if relevant_actions-{0,1}:c['optimistic_support_prior_nonturn_strict_task_effect']+=1
                        for alt in alts:
                            by_action[alt]['supported']+=1
                            by_action[alt]['supported_with_prior_strict_task_effect']+=int(alt in relevant_actions)
                    effects=original_effects(e)
                    for name,value in effects.items():c[name]+=int(value);by_action[a][name]+=int(value)
                    c['actions']+=1;by_action[a]['selected']+=1
                    if r>0:
                        c['positive_rewards']+=1
                        if not e['terminated']:c['positive_reward_not_terminal']+=1
                        positive=True
                    stat=row[a];stat[0]+=1;stat[1]+=int(effects['public_change'])
                    for k2,name in [(2,'door_open'),(3,'door_close'),(4,'target_first_visible'),(5,'target_pickup'),(6,'terminal_goal')]:stat[k2]+=int(effects[name])
                c['episodes']+=1
            c['distinct_native_contexts']=len(memory)
            rows.append({'role':role,'family':family,'seeds':[ep['seed_dev_exposed'] for ep in series],
                         'counts':dict(c),'by_action':{str(a):dict(t) for a,t in sorted(by_action.items())}})
    return rows

def main():
    p=argparse.ArgumentParser();p.add_argument('existing_archive');p.add_argument('--output',required=True)
    a=p.parse_args()
    if sha(a.existing_archive)!=ZIP_SHA:raise ValueError('PINNED_SOURCE_ARCHIVE_BYTES_CHANGED')
    with zipfile.ZipFile(a.existing_archive) as z:
        if not {'first.json','second.json','comparison.log'}.issubset(z.namelist()):raise ValueError('ORIGINAL_PROCESSES_MISSING')
        try:
            import orjson
            loads=orjson.loads
        except ImportError:loads=json.loads
        first=loads(z.read('first.json'));rows=census(first);del first
        second=loads(z.read('second.json'));other=census(second);del second
        if other!=rows:raise ValueError('INDEPENDENT_SOURCE_PROCESS_COUNTS_DIVERGED')
    keys=sorted({key for row in rows for key in row['counts']})
    totals={key:sum(row['counts'].get(key,0) for row in rows) for key in keys}
    result={'schema':'nr-m1p-authentic-task-effect-attribution-v1',
            'classification':'RETROSPECTIVE_DEV_SOURCE_EFFECT_NOT_NATIVE_MG28_POLICY',
            'prereg_commit':'3048d45c53b46e9b8e14237165f77f2e0e6ce473',
            'original_zip_sha256':ZIP_SHA,'canonical_source_sha256':SOURCE_SHA,
            'both_independent_original_processes_match':True,'no_environment_actions':True,
            'role_family_rows':rows,'totals':totals}
    with open(a.output,'w') as f:json.dump(result,f,sort_keys=True,indent=2);f.write('\n')
    print(json.dumps(totals,sort_keys=True))

if __name__=='__main__':main()
