"""Small standalone reproduction of ELG-01A9's two symbolic controls.
Original full PyTorch/GRU source has distinct immutable SHA in RESULTS.md.
Full-sentence targets only; fixed binary-AST and triple-order priors.
"""
import collections, hashlib, json, random
N=['ambra','bex','corin','daro','elmi','fenn','gala','hesp']
V=['mended','pushed','tested','observed','guided','warned','followed']
O=['apex','brim','cove','dune','ember','fjord','grove','haven']
OPS=('K0','K1','K2'); JOIN=('afterward','since','although')
TRUTH={'K0':('afterward',0),'K1':('since',1),'K2':('although',0)}
def leaf(r):return ('E',f'S{r.randrange(len(N))}',f'V{r.randrange(len(V))}',f'O{r.randrange(len(O))}')
def tree(r,n):
 if n==1:return leaf(r)
 a=r.randrange(1,n)
 return (r.choice(OPS),tree(r,a),tree(r,n-a))
def render(t,lex,rules):
 if t[0]=='E':return [lex[v] for v in t[1:]]
 w,reverse=rules[t[0]];a,b=render(t[1],lex,rules),render(t[2],lex,rules)
 if reverse:a,b=b,a
 return ['(']+a+[w]+b+[')']
def corpus():
 r=random.Random(20261023)
 train=[leaf(r) for _ in range(384)]+[tree(r,2) for _ in range(720)]
 dev=[tree(r,4) for _ in range(192)]
 source_lex={**{f'S{i}':x for i,x in enumerate(N)},**{f'V{i}':x for i,x in enumerate(V)},**{f'O{i}':x for i,x in enumerate(O)}}
 return train,dev,source_lex

def fit(train,text,elimination=False):
 lex={}
 for t,y in zip(train,text):
  if t[0]=='E':
   for k,v in zip(t[1:],y):
    if k in lex:assert lex[k]==v
    lex[k]=v
 rules={}
 for op in OPS:
  rows=[(t,y) for t,y in zip(train,text) if t[0]==op]
  options=[(c,reverse) for c in JOIN for reverse in (0,1)]
  if elimination:
   for t,y in rows:options=[a for a in options if render(t,lex,{op:a})==y]
   assert len(options)==1;rules[op]=options[0]
  else:
   counts=[sum(render(t,lex,{op:a})==y for t,y in rows) for a in options]
   assert max(counts)==len(rows);rules[op]=options[counts.index(max(counts))]
 return lex,rules

def main():
 tr,dv,oracle_lex=corpus()
 assert len(tr)==1104 and len(dv)==192
 assert not {json.dumps(x) for x in tr}&{json.dumps(x) for x in dv}
 gold=[render(t,oracle_lex,TRUTH) for t in tr]
 dev_gold=[render(t,oracle_lex,TRUTH) for t in dv]
 for elimination in (False,True):
  lex,rules=fit(tr,gold,elimination)
  out=[render(t,lex,rules) for t in dv]
  print('exhaustive control' if elimination else 'factorized learner',sum(a==b for a,b in zip(out,dev_gold)),'/',len(dv))
if __name__=='__main__':main()
