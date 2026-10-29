// ACC-35: native Go, source-free reversible history memory; no production model.
package main

import (
 "bytes"
 "compress/zlib"
 "crypto/sha256"
 "encoding/binary"
 "encoding/hex"
 "encoding/json"
 "errors"
 "fmt"
 "io"
 "math"
 "os"
 "os/exec"
 "runtime"
 "sort"
 "strconv"
 "time"
)

const schema = "forge.acc35.acd3.native-go-reversible-history-sourcefree.v1"
const sessions = 16
const histories = 1024
const length = 64
type counts [2]uint32
type edge struct { label []byte; next *node }
type node struct { count counts; terminal bool; edges []edge }
type radix struct { root *node; splits int }
func newRadix()*radix{return &radix{root:&node{}}}
func common(a,b []byte)int{n:=len(a);if len(b)<n{n=len(b)};i:=0;for i<n&&a[i]==b[i]{i++};return i}
func (r *radix) add(key []byte,label int){
 cur:=r.root
 for {
  if len(key)==0 {cur.count[label]++;cur.terminal=true;return}
  match:=-1
  for i,e:=range cur.edges {if e.label[0]==key[0]{match=i;break}}
  if match<0 {
   next:=&node{terminal:true};next.count[label]++
   cur.edges=append(cur.edges,edge{label:bytes.Clone(key),next:next})
   return
  }
  e:=cur.edges[match];n:=common(e.label,key)
  if n==len(e.label){key=key[n:];cur=e.next;continue}
  if n==0{panic("radix impossible disjoint first byte")}
  mid:=&node{edges:[]edge{{label:bytes.Clone(e.label[n:]),next:e.next}}}
  cur.edges[match]=edge{label:bytes.Clone(e.label[:n]),next:mid}
  r.splits++
  key=key[n:]
  if len(key)==0 {mid.terminal=true;mid.count[label]++} else {
   child:=&node{terminal:true};child.count[label]++
   mid.edges=append(mid.edges,edge{label:bytes.Clone(key),next:child})
  }
  return
 }
}
func (r *radix) find(key []byte)(counts,bool){
 cur:=r.root
 for len(key)>0 {
  found:=false
  for _,e:=range cur.edges{
   if bytes.HasPrefix(key,e.label){
    key=key[len(e.label):];cur=e.next;found=true;break
   }
  }
  if !found{return counts{},false}
 }
 return cur.count,cur.terminal
}
func putVar(b *bytes.Buffer,v uint64){var scratch [10]byte;n:=binary.PutUvarint(scratch[:],v);b.Write(scratch[:n])}
func writeNode(b *bytes.Buffer,n *node){
 if n.terminal{b.WriteByte(1)}else{b.WriteByte(0)}
 putVar(b,uint64(n.count[0]));putVar(b,uint64(n.count[1]))
 sorted:=append([]edge(nil),n.edges...)
 sort.Slice(sorted,func(i,j int)bool{return bytes.Compare(sorted[i].label,sorted[j].label)<0})
 putVar(b,uint64(len(sorted)))
 for _,e:=range sorted{putVar(b,uint64(len(e.label)));b.Write(e.label);writeNode(b,e.next)}
}
func (r *radix) snapshot []byte{var b bytes.Buffer;b.WriteString("AC35R1");writeNode(&b,r.root);return b.Bytes()}
func readNode(rd *bytes.Reader,depth int)(*node,error){
 if depth>64{return nil,errors.New("ACC35_RADIX_DEPTH")}
 flag,e:=rd.ReadByte();if e!=nil||flag>1{return nil,errors.New("ACC35_RADIX_TERMINAL")}
 a,e:=binary.ReadUvarint(rd);if e!=nil||a>histories{return nil,errors.New("ACC35_RADIX_COUNTS")}
 b,e:=binary.ReadUvarint(rd);if e!=nil||b>histories{return nil,errors.New("ACC35_RADIX_COUNTS")}
 number,e:=binary.ReadUvarint(rd);if e!=nil||number>256{return nil,errors.New("ACC35_RADIX_BRANCHES")}
 n:=&node{terminal:flag==1,count:counts{uint32(a),uint32(b)}}
 for i:=0;i<int(number);i++{
  size,e:=binary.ReadUvarint(rd);if e!=nil||size==0||size>64{return nil,errors.New("ACC35_RADIX_LABEL")}
  label:=make([]byte,int(size));if _,e=io.ReadFull(rd,label);e!=nil{return nil,e}
  child,e:=readNode(rd,depth+1);if e!=nil{return nil,e}
  n.edges=append(n.edges,edge{label:label,next:child})
 }
 return n,nil
}
func restoreRadix(data []byte)(*radix,error){
 if len(data)>2_000_000||!bytes.HasPrefix(data,[]byte("AC35R1")){return nil,errors.New("ACC35_RADIX_SNAPSHOT_HEADER")}
 rd:=bytes.NewReader(data[6:])
 n,e:=readNode(rd,0);if e!=nil||rd.Len()!=0{return nil,errors.New("ACC35_RADIX_SNAPSHOT_INVALID")}
 r:=&radix{root:n}
 if !bytes.Equal(r.snapshot(),data){return nil,errors.New("ACC35_RADIX_NONCANONICAL")}
 return r,nil
}
type record struct { key [length]byte; label int }
func rng(seed *uint64)uint64{*seed^=*seed<<13;*seed^=*seed>>7;*seed^=*seed<<17;return *seed}
func makeHistory(seed *uint64,i int,scenario string)([length]byte,int){
 var key [length]byte
 group:=(i*7+3)%16
 x:=uint64(group+1)*0x9e3779b97f4a7c15
 for j:=0;j<40;j++{key[j]=byte(rng(&x)%8+'A')}
 // late suffix is independent within prefix and cannot be inferred from FIT prefix.
 for j:=40;j<64;j++{key[j]=byte(rng(seed)%16+'a')}
 binary.LittleEndian.PutUint32(key[40:44],uint32(i))
 label:=group%2
 if scenario=="DELAYED"{label=int(key[63]&1)}
 return key,label
}
func makeRecords(scenario string,session int)[]record{
 seed:=uint64(0x97d156a1)+uint64(session)*0x9e3779b97f4a7c15
 out:=make([]record,histories)
 for i:=range out{key,label:=makeHistory(&seed,i,scenario);out[i]=record{key,label}}
 return out
}
func rawMap(records []record)map[string]counts{
 m:=make(map[string]counts,len(records))
 for _,r:=range records{key:=string(r.key[:]);c:=m[key];c[r.label]++;m[key]=c}
 return m
}
func rawSnapshot(m map[string]counts)[]byte{
 keys:=make([]string,0,len(m));for k:=range m{keys=append(keys,k)};sort.Strings(keys)
 b:=make([]byte,0,len(m)*72)
 b=append(b,[]byte("AC35RAW1")...)
 for _,k:=range keys{b=append(b,k...);c:=m[k];var v [8]byte
  binary.LittleEndian.PutUint32(v[:4],c[0]);binary.LittleEndian.PutUint32(v[4:],c[1]);b=append(b,v[:]...)}
 return b
}
func rawRestore(snapshot []byte)(map[string]counts,error){
 if !bytes.HasPrefix(snapshot,[]byte("AC35RAW1"))||(len(snapshot)-8)%72!=0{return nil,errors.New("ACC35_RAW_SNAPSHOT_INVALID")}
 m:=make(map[string]counts)
 for p:=8;p<len(snapshot);p+=72{
  k:=string(snapshot[p:p+64])
  if _,ok:=m[k];ok{return nil,errors.New("ACC35_RAW_DUPLICATE")}
  m[k]=counts{binary.LittleEndian.Uint32(snapshot[p+64:p+68]),binary.LittleEndian.Uint32(snapshot[p+68:p+72])}
 }
 return m,nil
}
func compress(in []byte)([]byte,error){
 var b bytes.Buffer
 z,e:=zlib.NewWriterLevel(&b,zlib.BestSpeed);if e!=nil{return nil,e}
 if _,e=z.Write(in);e!=nil{return nil,e}
 if e=z.Close();e!=nil{return nil,e}
 return b.Bytes(),nil
}
func decompress(in []byte)([]byte,error){
 zr,e:=zlib.NewReader(bytes.NewReader(in));if e!=nil{return nil,e}
 defer zr.Close()
 // Guard against unconstrained malicious checkpoint expansion.
 return io.ReadAll(io.LimitReader(zr,2_000_001))
}
type worker struct {
 Mode string `json:"mode"`
 Scenario string `json:"scenario"`
 Trial int `json:"trial"`
 Sessions int `json:"sessions"`
 Events int `json:"events"`
 Queries int `json:"queries"`
 Wrong int `json:"wrong"`
 Splits int `json:"splits"`
 DelayedContradictoryGroups int `json:"delayed_contradictory_groups"`
 SnapshotBytes int `json:"snapshot_bytes"`
 TotalAllocBytes uint64 `json:"total_alloc_bytes"`
 RuntimeSysBytes uint64 `json:"runtime_sys_bytes"`
 Digest string `json:"digest"`
}
func runWorker(mode,scenario string,trial int)(worker,error){
 if mode!="raw"&&mode!="radix"&&mode!="zlib"&&mode!="unsafe"{return worker{},errors.New("ACC35_UNKNOWN_MODE")}
 if scenario!="BENIGN"&&scenario!="DELAYED"||trial<0||trial>=3{return worker{},errors.New("ACC35_UNKNOWN_SCENARIO")}
 w:=worker{Mode:mode,Scenario:scenario,Trial:trial,Sessions:sessions}
 h:=sha256.New()
 var before,after runtime.MemStats
 runtime.ReadMemStats(&before)
 for iter:=0;iter<sessions;iter++{
  records:=makeRecords(scenario,iter+trial*31)
  original:=rawMap(records)
  prefixGroups:=map[string][2]bool{}
  for _,rec:=range records {k:=string(rec.key[:40]);v:=prefixGroups[k];v[rec.label]=true;prefixGroups[k]=v}
  if iter==0 {for _,labels:=range prefixGroups{if labels[0]&&labels[1]{w.DelayedContradictoryGroups++}}}
  var lookup func([]byte)(counts,bool)
  switch mode{
  case "raw":
   data:=rawSnapshot(original);w.SnapshotBytes+=len(data)
   restored,e:=rawRestore(data);if e!=nil{return worker{},e}
   lookup=func(k []byte)(counts,bool){v,ok:=restored[string(k)];return v,ok}
  case "zlib":
   data,e:=compress(rawSnapshot(original));if e!=nil{return worker{},e}
   w.SnapshotBytes+=len(data)
   payload,e:=decompress(data);if e!=nil{return worker{},e}
   restored,e:=rawRestore(payload);if e!=nil{return worker{},e}
   lookup=func(k []byte)(counts,bool){v,ok:=restored[string(k)];return v,ok}
  case "radix":
   tree:=newRadix()
   for _,rec:=range records{tree.add(rec.key[:],rec.label)}
   w.Splits+=tree.splits
   blob:=tree.snapshot();w.SnapshotBytes+=len(blob)
   restored,e:=restoreRadix(blob);if e!=nil{return worker{},e}
   lookup=restored.find
  case "unsafe":
   table:=map[string]counts{}
   for _,rec:=range records{key:=string(rec.key[:40]);c:=table[key];c[rec.label]++;table[key]=c}
   // No hidden record identities or provenance retained: deliberately unsafe.
   w.SnapshotBytes+=len(table)*48
   lookup=func(k []byte)(counts,bool){v,ok:=table[string(k[:40])];return v,ok}
  }
  for j:=0;j<512;j++{
   idx:=(j*13+iter*7)%len(records);key:=records[idx].key
   if j>=256{key[63]=byte('z');key[62]=byte('z')} // impossible for original suffix alphabet
   want,exists:=original[string(key[:])]
   got,ok:=lookup(key[:])
   if ok!=exists||got!=want{w.Wrong++}
   // Signed exact query result digest, not candidate's internal compression.
   var buf [10]byte;buf[0]=byte(j&255);if ok{buf[1]=1}
   binary.LittleEndian.PutUint32(buf[2:6],got[0])
   binary.LittleEndian.PutUint32(buf[6:10],got[1])
   _,_=h.Write(buf[:])
   w.Queries++
  }
  w.Events+=len(records)
 }
 runtime.ReadMemStats(&after)
 w.TotalAllocBytes=after.TotalAlloc-before.TotalAlloc
 w.RuntimeSysBytes=after.Sys
 w.Digest=hex.EncodeToString(h.Sum(nil))
 return w,nil
}
type trialResult struct{
 Mode string `json:"mode"`;Scenario string `json:"scenario"`;Trial int `json:"trial"`
 CPUSeconds float64 `json:"cpu_seconds"`;WallSeconds float64 `json:"wall_seconds"`
 Worker worker `json:"worker"`
}
type summary struct{
 Scenario string `json:"scenario"`
 RadixCPUOverRaw float64 `json:"radix_cpu_over_raw"`
 RadixBytesOverRaw float64 `json:"radix_bytes_over_raw"`
 RadixBytesOverZlib float64 `json:"radix_bytes_over_zlib"`
 ExactColdRestore bool `json:"exact_cold_restore"`
 UnsafeWrong int `json:"unsafe_wrong"`
 RadixSplits int `json:"radix_splits"`
 LateContradictions int `json:"late_contradictions"`
}
func median(v []float64)float64{sort.Float64s(v);return v[len(v)/2]}
func report()(any,error){
 var results []trialResult
 for _,scenario:=range []string{"BENIGN","DELAYED"}{
  for t:=0;t<3;t++{
   modes:=[]string{"raw","radix","zlib","unsafe"}
   if t%2==1{modes=[]string{"unsafe","zlib","radix","raw"}}
   for _,mode:=range modes{
    child:=exec.Command(os.Args[0],"worker",mode,scenario,strconv.Itoa(t))
    start:=time.Now();payload,e:=child.Output();wall:=time.Since(start)
    if e!=nil{return nil,fmt.Errorf("ACC35_CHILD_FAIL %s %s %d: %w",scenario,mode,t,e)}
    st:=child.ProcessState
    cpu:=st.UserTime()+st.SystemTime()
    if cpu<=0{return nil,errors.New("ACC35_CHILD_CPU_UNAVAILABLE")}
    var w worker
    if e=json.Unmarshal(payload,&w);e!=nil{return nil,e}
    if w.Mode!=mode||w.Scenario!=scenario||w.Trial!=t||w.Events!=1024*16||w.Queries!=512*16||w.Sessions!=16||w.SnapshotBytes<=0{
     return nil,errors.New("ACC35_WORKER_CONTRACT_DRIFT")
    }
    results=append(results,trialResult{mode,scenario,t,cpu.Seconds(),wall.Seconds(),w})
   }
  }
 }
 summaries:=[]summary{}
 qualified:=true
 for _,scenario:=range []string{"BENIGN","DELAYED"}{
  var cpu,rawBytes,zBytes []float64
  s:=summary{Scenario:scenario,ExactColdRestore:true}
  for t:=0;t<3;t++{
   by:=map[string]trialResult{}
   for _,r:=range results{if r.Scenario==scenario&&r.Trial==t{by[r.Mode]=r}}
   if len(by)!=4{return nil,errors.New("ACC35_MISSING_MATCHED_WORKERS")}
   for _,mode:=range []string{"raw","radix","zlib"}{
    if by[mode].Worker.Wrong!=0||by[mode].Worker.Digest!=by["raw"].Worker.Digest{
     s.ExactColdRestore=false
    }
   }
   s.UnsafeWrong+=by["unsafe"].Worker.Wrong
   s.RadixSplits+=by["radix"].Worker.Splits
   s.LateContradictions+=by["radix"].Worker.DelayedContradictoryGroups
   cpu=append(cpu,by["radix"].CPUSeconds/by["raw"].CPUSeconds)
   rawBytes=append(rawBytes,float64(by["radix"].Worker.SnapshotBytes)/float64(by["raw"].Worker.SnapshotBytes))
   zBytes=append(zBytes,float64(by["radix"].Worker.SnapshotBytes)/float64(by["zlib"].Worker.SnapshotBytes))
  }
  s.RadixCPUOverRaw=median(cpu)
  s.RadixBytesOverRaw=median(rawBytes)
  s.RadixBytesOverZlib=median(zBytes)
  if !s.ExactColdRestore||s.RadixSplits==0||s.RadixCPUOverRaw>1.15||s.RadixBytesOverRaw>0.75||s.RadixBytesOverZlib>1.00||
   (scenario=="DELAYED"&&(s.UnsafeWrong==0||s.LateContradictions==0)){
   qualified=false
  }
  summaries=append(summaries,s)
 }
 decision:="ACC35_ACD3_NO_CROSSHOST_TOTAL_CPU_AND_STRONG_COMPRESSION_WIN"
 if qualified{decision="ACC35_ACD3_NATIVE_GO_SOURCEFREE_RESOURCE_POSITIVE_NOT_MODEL"}
 return struct{
  Schema string `json:"schema"`
  Candidate string `json:"candidate"`
  TotalPortfolio int `json:"total_portfolio"`
  OriginalNativeModelIntegrated bool `json:"original_native_model_integrated"`
  ScientificFirstUse bool `json:"scientific_first_use"`
  ScientificAdmission bool `json:"scientific_admission"`
  OSRSSMeasured bool `json:"os_peak_rss_measured"`
  Trials []trialResult `json:"trials"`
  Summaries []summary `json:"summaries"`
  Classification string `json:"classification"`
 }{schema,"AC-D3",36,false,false,false,false,results,summaries,decision},nil
}
func main(){
 if len(os.Args)>1&&os.Args[1]=="worker"{
  if len(os.Args)!=5{panic("ACC35_WORKER_ARGS")}
  t,e:=strconv.Atoi(os.Args[4]);if e!=nil{panic(e)}
  w,e:=runWorker(os.Args[2],os.Args[3],t);if e!=nil{panic(e)}
  if e=json.NewEncoder(os.Stdout).Encode(w);e!=nil{panic(e)}
  return
 }
 if len(os.Args)!=2||os.Args[1]!="report"{panic("usage: acc35 report")}
 r,e:=report();if e!=nil{fmt.Fprintln(os.Stderr,e);os.Exit(2)}
 if e=json.NewEncoder(os.Stdout).Encode(r);e!=nil{panic(e)}
 // Preserve all negative outputs in JSON; never mark scientific model admission.
 _=math.MaxFloat64
}
