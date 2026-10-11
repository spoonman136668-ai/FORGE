package pilotf4

import "errors"

// Primary constructs a prospective original. It must not be called in source
// qualification or CI tests. Only an independently released one-shot workflow
// may invoke this after both lanes have externally archived STARTED.
func Primary(lane,runID,sourceSHA string,f Frozen)(Raw,error){
 if lane!="Wingless"&&lane!="Yggdrasil"||!validSource(sourceSHA)||runID==""||len(runID)>24{return Raw{},ErrInvalid}
 for _,ch:=range runID{if ch<'0'||ch>'9'{return Raw{},ErrInvalid}}
 raw:=Raw{Schema:RawSchema,Generation:"F4",Lane:lane,SourceSHA:sourceSHA,
  RunID:runID,FreezeBlob:FreezeBlob,SyntheticOnly:true}
 if lane=="Wingless"{
  for i,seed:=range f.Wingless.Hold{
   raw.Rows=append(raw.Rows,runWinglessRow(f.Wingless.Train[i],seed))
  }
 }else{
  for i,seed:=range f.Yggdrasil.Hold{
   raw.Rows=append(raw.Rows,runYggdrasilRow(f.Yggdrasil.Train[i],seed))
  }
 }
 if len(raw.Rows)==0{return Raw{},errors.New("F4_NO_ORIGINAL_ROWS")}
 return raw,nil
}
func permF4(n,seed int)[]int{
 p:=make([]int,n);for i:=range p{p[i]=i}
 x:=uint64(seed)
 for i:=n-1;i>0;i--{
  x=x*6364136223846793005+1442695040888963407
  j:=int((x>>32)%uint64(i+1));p[i],p[j]=p[j],p[i]
 }
 return p
}
func affineF4(role,x int)int{return ((2*role+3)*x+(7*role+1))%29}
func trainAffineF4(role,trainingSeed int)([2]int,bool){
 // Demonstrations are generated before querying heldout inputs. Infer a
 // unique affine mapping from observed pairs rather than reading test labels.
 x0:=(trainingSeed+role*3)%29
 x1:=(x0+7)%29
 y0,y1:=affineF4(role,x0),affineF4(role,x1)
 var found [2]int
 n:=0
 for a:=0;a<29;a++{for b:=0;b<29;b++{
  if (a*x0+b)%29==y0&&(a*x1+b)%29==y1{
   found=[2]int{a,b};n++
  }
 }}
 return found,n==1
}
func applyAffineF4(ab [2]int,x int)int{return (ab[0]*x+ab[1])%29}
func runWinglessRow(train,held int)Row{
 left,right:=permF4(5,held),permF4(5,held+101)
 r:=Row{TrainSeed:train,HeldoutSeed:held,Cases:240,Bounded:true}
 for i:=0;i<240;i++{
  ctx:=(i+held)%2;a:=i%5;b:=(3*i+1)%5
  if a==b{b=(b+1)%5}
  x:=(7*i+held)%29
  mapping:=left;if ctx==1{mapping=right}
  truth:=affineF4(mapping[b],affineF4(mapping[a],x))
  // A context-specific role table and equal-capacity non-context baseline.
  adapted:=applyAffineF4(learned[ctx][b],applyAffineF4(learned[ctx][a],x))
  unkeyed:=affineF4(right[b],affineF4(right[a],x))
  reverse:=affineF4(mapping[a],affineF4(mapping[b],x))
  if adapted==truth{r.Correct++}
  if unkeyed==truth{r.Baseline++}
  if reverse==truth{r.Control++}
 }
 return r
}
type f4Mem struct{pinned map[int]bool;recent map[int]bool;order []int;cap int}
func f4NewMem(c int)*f4Mem{return &f4Mem{pinned:map[int]bool{},recent:map[int]bool{},cap:c}}
func (m *f4Mem)put(k int){
 if m.pinned[k]{return}
 if m.recent[k]{
  for i,x:=range m.order{if x==k{m.order=append(m.order[:i],m.order[i+1:]...);break}}
 }else if len(m.order)>=m.cap{
  delete(m.recent,m.order[0]);m.order=m.order[1:]
 }
 m.recent[k]=true;m.order=append(m.order,k)
}
func (m *f4Mem)has(k int)bool{return m.pinned[k]||m.recent[k]}
func runYggdrasilRow(train,held int)Row{
 acquired:=permF4(20,train)
 protected,lru:=f4NewMem(6),f4NewMem(12)
 for i,k:=range acquired{
  if i<6{protected.pinned[k]=true}else{protected.put(k)}
  lru.put(k)
 }
 for burst:=0;burst<5;burst++{
  hot:=permF4(20,held+burst*1063)
  for _,k:=range hot[:12]{protected.put(k);lru.put(k)}
 }
 r:=Row{TrainSeed:train,HeldoutSeed:held,Cases:20}
 for _,k:=range acquired[:6]{
  if protected.has(k){r.Correct++}
  if lru.has(k){r.Baseline++}
 }
 hot:=permF4(20,held+4*1063)
 for _,k:=range hot[:12]{if protected.has(k){r.Hot++}}
 r.Bounded=len(protected.pinned)+len(protected.recent)<=12&&len(lru.recent)<=12
 return r
}
