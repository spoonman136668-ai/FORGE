// Package hostedcompute verifies bounded, source-pinned, NONSCIENTIFIC
// GitHub-hosted compute handoffs. It is not an FSA, broker, dispatcher,
// research experiment, accepted-science log, or protected storage.
package hostedcompute

import (
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "fmt"
 "runtime"
 "sort"
 "strconv"
 "strings"
)

const (
 ManifestSchema="forge.hostedcompute.shadow-manifest.v1"
 ReceiptSchema="forge.hostedcompute.shadow-receipt.v1"
 SummarySchema="forge.hostedcompute.shadow-reconciled.v1"
 Mode="NONSCIENTIFIC_SHADOW_NO_FSA_AUTHORITY"
 WorkUnits=4096
)
var ErrUntrusted=errors.New("FORGE_HOSTED_SHADOW_IDENTITY_OR_AUTHORITY_INVALID")
var ErrCorrupt=errors.New("FORGE_HOSTED_SHADOW_RECEIPT_INCOMPLETE_OR_DUPLICATE")

type WorkItem struct {
 Lane string
 OS string
 Units int
 InputSHA256 string
}
type Manifest struct {
 Schema string
 Mode string
 SourceSHA string
 SourceTreeSHA string
 RunID string
 RunAttempt int
 Work []WorkItem
 ManifestSHA256 string
}
type Receipt struct {
 Schema string
 Mode string
 ManifestSHA256 string
 SourceSHA string
 SourceTreeSHA string
 RunID string
 RunAttempt int
 Lane string
 OS string
 WorkerLabel string
 Units int
 InputSHA256 string
 OutputSHA256 string
 ScientificOriginal bool
 FSAAdmission bool
 DispatchAuthorized bool
}
type Summary struct {
 Schema string
 Mode string
 ManifestSHA256 string
 SourceSHA string
 SourceTreeSHA string
 RunID string
 RunAttempt int
 ReceiptSHA256 []string
 AcceptedShadowJobs int
 OriginalExperimentsConsumed int
 ScientificallyQualified bool
 FSAActivated bool
 ScientificDispatchAuthorized bool
 PhysicalTrustIndependenceProven bool
 RetentionDurabilityProven bool
}
func hash(b []byte)string {d:=sha256.Sum256(b);return hex.EncodeToString(d[:])}
func validHex(s string,n int)bool{
 if len(s)!=n{return false}
 for _,ch:=range s{if !((ch>='0'&&ch<='9')||(ch>='a'&&ch<='f')){return false}}
 return true
}
func validRun(s string)bool{
 if len(s)<1||len(s)>20||s[0]=='0'{return false}
 for _,ch:=range s{if ch<'0'||ch>'9'{return false}}
 n,err:=strconv.ParseUint(s,10,64)
 return err==nil&&n>0
}
func key(lane,os string)string{return lane+"-"+os}
func workKey(lane,os,source,tree string)string{
 return hash([]byte("FORGE_R8_SHADOW_INPUT_V1\x00"+lane+"\x00"+os+"\x00"+source+"\x00"+tree))
}
func core(m Manifest) Manifest {m.ManifestSHA256="";return m}
func manifestHash(m Manifest)string{b,_:=json.Marshal(core(m));return hash(b)}
func expectedItems(source,tree string)[]WorkItem{
 out:=make([]WorkItem,0,4)
 for _,lane:=range []string{"Wingless","Yggdrasil"}{
  for _,os:=range []string{"linux","windows"}{
   out=append(out,WorkItem{Lane:lane,OS:os,Units:WorkUnits,
    InputSHA256:workKey(lane,os,source,tree)})
  }
 }
 return out
}
func MakeManifest(source,tree,run string,attempt int)(Manifest,error){
 var zero Manifest
 if !validHex(source,40)||!validHex(tree,40)||!validRun(run)||attempt!=1{
  return zero,ErrUntrusted
 }
 m:=Manifest{Schema:ManifestSchema,Mode:Mode,
  SourceSHA:source,SourceTreeSHA:tree,RunID:run,
  RunAttempt:attempt,Work:expectedItems(source,tree)}
 m.ManifestSHA256=manifestHash(m)
 return m,nil
}
func ValidateManifest(m Manifest)error{
 if m.Schema!=ManifestSchema||m.Mode!=Mode||
  !validHex(m.SourceSHA,40)||!validHex(m.SourceTreeSHA,40)||
  !validRun(m.RunID)||m.RunAttempt!=1||
  len(m.Work)!=4||!validHex(m.ManifestSHA256,64)||
  manifestHash(m)!=m.ManifestSHA256{return ErrUntrusted}
 want:=expectedItems(m.SourceSHA,m.SourceTreeSHA)
 for i,item:=range m.Work{
  if item!=want[i]{return ErrUntrusted}
 }
 return nil
}
func computeDigest(input string,units int)(string,error){
 if !validHex(input,64)||units!=WorkUnits{return "",ErrUntrusted}
 current,_:=hex.DecodeString(input)
 for i:=0;i<units;i++{
  b:=make([]byte,0,len(current)+4)
  b=append(b,current...)
  b=append(b,byte(i>>24),byte(i>>16),byte(i>>8),byte(i))
  sum:=sha256.Sum256(b)
  current=sum[:]
 }
 return hex.EncodeToString(current),nil
}
func expectedWorker(lane,os string)string{
 return "forge-r8-"+strings.ToLower(lane)+"-"+os
}
func RunShadow(m Manifest,source,tree,run string,attempt int,lane,os,worker string)(Receipt,error){
 var zero Receipt
 if ValidateManifest(m)!=nil||source!=m.SourceSHA||
  tree!=m.SourceTreeSHA||run!=m.RunID||attempt!=m.RunAttempt||
  worker!=expectedWorker(lane,os)||os!=runtime.GOOS{
  return zero,ErrUntrusted
 }
 var w WorkItem
 found:=false
 for _,item:=range m.Work{
  if item.Lane==lane&&item.OS==os{w=item;found=true;break}
 }
 if !found{return zero,ErrUntrusted}
 digest,err:=computeDigest(w.InputSHA256,w.Units)
 if err!=nil{return zero,err}
 return Receipt{
  Schema:ReceiptSchema,Mode:Mode,
  ManifestSHA256:m.ManifestSHA256,
  SourceSHA:source,SourceTreeSHA:tree,RunID:run,RunAttempt:attempt,
  Lane:lane,OS:os,WorkerLabel:worker,Units:w.Units,
  InputSHA256:w.InputSHA256,OutputSHA256:digest,
 },nil
}
func VerifyReceipt(m Manifest,r Receipt)error{
 if ValidateManifest(m)!=nil||r.Schema!=ReceiptSchema||r.Mode!=Mode||
  r.ManifestSHA256!=m.ManifestSHA256||r.SourceSHA!=m.SourceSHA||
  r.SourceTreeSHA!=m.SourceTreeSHA||r.RunID!=m.RunID||
  r.RunAttempt!=m.RunAttempt||r.WorkerLabel!=expectedWorker(r.Lane,r.OS)||
  r.ScientificOriginal||r.FSAAdmission||r.DispatchAuthorized{return ErrUntrusted}
 found:=false
 for _,w:=range m.Work{
  if w.Lane==r.Lane&&w.OS==r.OS{
   if w.Units!=r.Units||w.InputSHA256!=r.InputSHA256{return ErrCorrupt}
   found=true;break
  }
 }
 if !found{return ErrUntrusted}
 digest,err:=computeDigest(r.InputSHA256,r.Units)
 if err!=nil||digest!=r.OutputSHA256{return ErrCorrupt}
 return nil
}
func Reconcile(m Manifest,receipts []Receipt)(Summary,error){
 var zero Summary
 if ValidateManifest(m)!=nil||len(receipts)!=4{return zero,ErrCorrupt}
 seen:=map[string]bool{}
 addresses:=make([]string,0,4)
 for _,r:=range receipts{
  if err:=VerifyReceipt(m,r);err!=nil{return zero,err}
  k:=key(r.Lane,r.OS)
  if seen[k]{return zero,ErrCorrupt}
  seen[k]=true
  b,err:=json.Marshal(r)
  if err!=nil{return zero,ErrCorrupt}
  addresses=append(addresses,hash(b))
 }
 for _,w:=range m.Work{
  if !seen[key(w.Lane,w.OS)]{return zero,ErrCorrupt}
 }
 sort.Strings(addresses)
 return Summary{
  Schema:SummarySchema,Mode:Mode,
  ManifestSHA256:m.ManifestSHA256,
  SourceSHA:m.SourceSHA,SourceTreeSHA:m.SourceTreeSHA,
  RunID:m.RunID,RunAttempt:m.RunAttempt,
  ReceiptSHA256:addresses,AcceptedShadowJobs:4,
 },nil
}
func (m Manifest)Describe()string{
 return fmt.Sprintf("%s source=%s tree=%s run=%s attempt=%d units_per_worker=%d",
  Mode,m.SourceSHA,m.SourceTreeSHA,m.RunID,m.RunAttempt,WorkUnits)
}
