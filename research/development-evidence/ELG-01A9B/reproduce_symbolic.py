"""ELG-01A9B symbolic demonstration (development, not scientific first-use)."""
import collections, hashlib, json, random
N=['ambra','bex','corin','daro','elmi','fenn','gala','hesp']
V=['mended','pushed','tested','observed','guided','warned','followed']
O=['apex','brim','cove','dune','ember','fjord','grove','haven']
R={'K0':('afterward',0),'K1':('since',1),'K2':('although',0)}
J=('afterward','since','although')
def leaf(r):return ('E',f'S{r.randrange(len(N))}',f'V{r.randrange(len(V))}',f'O{r.randrange(len(O))}')
def tree(r,n):
 if n==1:return leaf(r)
 k=r.randrange(1,n);return (r.choice(tuple(R)),tree(r,k),tree(r,n-k))
def source(t):return list(t[1:]) if t[0]=='E' else [t[0]]+source(t[1])+source(t[2])
def gold(t):
 if t[0]=='E':return [N[int(t[1][1:])],V[int(t[2][1:])],O[int(t[3][1:])]]
 word,reverse=R[t[0]];a,b=gold(t[1]),gold(t[2]);a,b=(b,a) if reverse else (a,b)
 return ['(']+a+[word]+b+[')']
def sha(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def corpus():
 r=random.Random(20261024)
 return [leaf(r) for _ in range(384)]+[tree(r,2) for _ in range(720)],[tree(r,5) for _ in range(192)]
def learn(rows,texts):
 width=min(map(len,rows));lex={}
 for p,y in zip(rows,texts):
  if len(p)==width:
   assert len(y)==width
   for x,z in zip(p,y):
    assert x not in lex or lex[x]==z
    lex[x]=z
 ops=set().union(*map(set,rows))-set(lex)
 valid=[b for b in range(1,5) if all((len(p)-sum(t in ops for t in p))//width==1+sum(t in ops for t in p)*(b-1) and (len(p)-sum(t in ops for t in p))%width==0 for p in rows)]
 assert len(valid)==1;arity=valid[0]
 def parse(p):
  def rec(i):
   if p[i] not in ops:return ('E',*p[i:i+width]),i+width
   head=p[i];child=[];i+=1
   for _ in range(arity):
    v,i=rec(i);child.append(v)
   return (head,*child),i
  v,end=rec(0);assert end==len(p);return v
 def render(t,rules):
  if t[0]=='E':return [lex[x] for x in t[1:]]
  word,rev=rules[t[0]];a,b=render(t[1],rules),render(t[2],rules)
  if rev:a,b=b,a
  return ['(']+a+[word]+b+[')']
 rules={}
 for op in sorted(ops):
  choices=[]
  for w in J:
   for rev in (0,1):
    if all(render(parse(p),{op:(w,rev)})==y for p,y in zip(rows,texts) if p[0]==op):choices.append((w,rev))
  assert len(choices)==1;rules[op]=choices[0]
 assert all(render(parse(p),rules)==y for p,y in zip(rows,texts))
 return width,arity,lex,rules,lambda p:render(parse(p),rules)
def main():
 tr,dev=corpus();sx=[source(t) for t in tr];yy=[gold(t) for t in tr];dx=[source(t) for t in dev]
 assert set(map(sha,sx)).isdisjoint(set(map(sha,dx)))
 width,arity,lex,rules,predict=learn(sx,yy)
 score=sum(predict(p)==gold(t) for p,t in zip(dx,dev))
 print(json.dumps({'candidate_exact':score,'total':len(dev),'leaf_width':width,'arity':arity,'rules':rules,'train_sha256':sha(sx),'dev_sha256':sha(dx)},sort_keys=True))
 assert score==192 and width==3 and arity==2
if __name__=='__main__':main()
