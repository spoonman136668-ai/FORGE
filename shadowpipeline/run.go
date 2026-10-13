// Package shadowpipeline executes a bounded INACTIVE end-to-end recovery
// evidence handoff for the TWO pre-existing Wingless and Yggdrasil lanes.
// There is no executor, owner grant, scientific retry, or repair dispatch.
package shadowpipeline

import (
 "bytes"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "io"
 "os"
 "path/filepath"
 "reflect"
 "sort"
 "strings"

 "github.com/spoonman136668-ai/forge/lanereview"
 "github.com/spoonman136668-ai/forge/lanewitness"
 "github.com/spoonman136668-ai/forge/shadowbridge"
 "github.com/spoonman136668-ai/forge/shadowoutbox"
 "github.com/spoonman136668-ai/forge/watchdog"
)

const BundleSchema="forge.shadow.witnessed-bundle.v1"
const ReportSchema="forge.shadow.pipeline-report.v1"
const FolderName="forge-shadow-recovery"
var ErrUnsafe=errors.New("FORGE_SHADOW_PIPELINE_REJECTED_NO_SCIENCE_ACTION")

type Request struct {
 NowUnix uint64
 Witnesses []lanewitness.Signed
 WitnessPins []lanewitness.Pinned
 Reviews []lanereview.SignedFinding
 ReviewerPins []lanereview.ReviewerPin
}
type Bundle struct {
 Schema string `json:"schema"`
 NowUnix uint64 `json:"now_unix"`
 Witnesses []lanewitness.Signed `json:"witnesses"`
 WitnessPins []lanewitness.Pinned `json:"witness_pins"`
 Reviews []lanereview.SignedFinding `json:"reviews"`
 ReviewerPins []lanereview.ReviewerPin `json:"reviewer_pins"`
}
type Report struct {
 Schema string `json:"schema"`
 Mode string `json:"mode"`
 BundleSHA256 string `json:"bundle_sha256"`
 IncidentHeadSHA256 string `json:"incident_head_sha256"`
 ManifestSHA256 string `json:"manifest_sha256"`
 Incidents int `json:"incidents"`
 ReversibleRepairCandidates int `json:"reversible_repair_candidates"`
 OriginalReconciliations int `json:"original_reconciliations"`
 ScientificSuccessorReviews int `json:"scientific_successor_reviews"`
 IntegrityBlocks int `json:"integrity_blocks"`
 VerifiedScientificCycles int `json:"verified_scientific_cycles"`
 OutboxIDs []string `json:"outbox_ids"`
}
const mode="INACTIVE_SHADOW_NO_SCIENCE_AUTHORITY"
const domain="FORGE-SHADOW-WITNESSED-BUNDLE-V1\n"

func bundleOf(req Request)Bundle {
 return Bundle{Schema:BundleSchema,NowUnix:req.NowUnix,Witnesses:req.Witnesses,WitnessPins:req.WitnessPins,Reviews:req.Reviews,ReviewerPins:req.ReviewerPins}
}
func bundleDigest(b Bundle)(string,error){
 raw,err:=json.Marshal(b);if err!=nil{return "",err}
 d:=sha256.Sum256(append([]byte(domain),raw...))
 return hex.EncodeToString(d[:]),nil
}
func evaluate(req Request)(lanewitness.Assessment,[]watchdog.AssessedIncident,[]watchdog.DurableIncident,watchdog.RecoveryBatch,error){
 a,items,err:=lanereview.AssessIndependent(req.NowUnix,req.Witnesses,req.WitnessPins,req.Reviews,req.ReviewerPins)
 if err!=nil{return a,nil,nil,watchdog.RecoveryBatch{},ErrUnsafe}
 batch,err:=watchdog.PrepareRecoveryBatch(items)
 if err!=nil{return a,nil,nil,watchdog.RecoveryBatch{},ErrUnsafe}
 chain:=[]watchdog.DurableIncident{}
 head:=strings.Repeat("0",64)
 for _,i:=range a.Incidents{
  chain,err=watchdog.AppendIncidentChain(chain,i,head)
  if err!=nil{return a,nil,nil,watchdog.RecoveryBatch{},ErrUnsafe}
  head=chain[len(chain)-1].RecordSHA256
 }
 return a,items,chain,batch,nil
}
func allowedRoot(root string)bool{
 if root==""||!filepath.IsAbs(root)||filepath.Base(filepath.Clean(root))!=FolderName{return false}
 clean:=filepath.Clean(root)
 // A symlinked destination can escape the isolated shadow evidence root.
 // Reject both unsafe existing roots and unexpected filesystem errors.
 if st,err:=os.Lstat(clean);err==nil{
  if !st.IsDir()||st.Mode()&os.ModeSymlink!=0{return false}
 }else if !errors.Is(err,os.ErrNotExist){return false}
 for _,part:=range strings.FieldsFunc(strings.ToLower(clean),func(r rune)bool{return r=='/'||r=='\\'}){
  switch part{case "ckbr","ckb-plane","ktrade","ktrade-external","research-runner","forge-fsa-trust":return false}
 }
 for dir:=filepath.Dir(clean);;dir=filepath.Dir(dir){
  st,err:=os.Lstat(dir)
  if err!=nil||!st.IsDir()||st.Mode()&os.ModeSymlink!=0{return false}
  if next:=filepath.Dir(dir);next==dir{break}
 }
 return true
}
func writeOnce(path string,v any)error{
 b,err:=json.Marshal(v);if err!=nil{return err}
 b=append(b,'\n')
 f,err:=os.OpenFile(path,os.O_CREATE|os.O_EXCL|os.O_WRONLY,0600)
 if err!=nil{return errors.Join(ErrUnsafe,err)}
 n,err:=f.Write(b)
 if err==nil&&n!=len(b){err=io.ErrShortWrite}
 if err==nil{err=f.Sync()}
 closeErr:=f.Close()
 if err!=nil||closeErr!=nil{return ErrUnsafe}
 return nil
}
func readCanonical(path string,v any)error{
 st,err:=os.Lstat(path)
 if err!=nil||!st.Mode().IsRegular()||st.Size()==0||st.Size()>1<<20{return ErrUnsafe}
 f,err:=os.Open(path);if err!=nil{return ErrUnsafe};defer f.Close()
 raw,err:=io.ReadAll(io.LimitReader(f,(1<<20)+1))
 if err!=nil||len(raw)>1<<20{return ErrUnsafe}
 dec:=json.NewDecoder(bytes.NewReader(raw));dec.DisallowUnknownFields()
 if dec.Decode(v)!=nil{return ErrUnsafe}
 var extra any
 if !errors.Is(dec.Decode(&extra),io.EOF){return ErrUnsafe}
 canonical,err:=json.Marshal(v)
 if err!=nil||!bytes.Equal(raw,append(canonical,'\n')){return ErrUnsafe}
 return nil
}
func sortedOutboxIDs(root string)([]string,error){
 rows,err:=os.ReadDir(root)
 if err!=nil{return nil,ErrUnsafe}
 ids:=make([]string,0,len(rows))
 for _,row:=range rows{
  name:=row.Name()
  if !row.Type().IsRegular()||len(name)!=69||!strings.HasSuffix(name,".json"){return nil,ErrUnsafe}
  ids=append(ids,strings.TrimSuffix(name,".json"))
 }
 sort.Strings(ids)
 return ids,nil
}
func reportFor(b Bundle,chain []watchdog.DurableIncident,batch watchdog.RecoveryBatch,manifestSHA string,ids []string)(Report,error){
 bundleSHA,err:=bundleDigest(b);if err!=nil{return Report{},ErrUnsafe}
 head,err:=watchdog.VerifyIncidentChain(chain);if err!=nil{return Report{},ErrUnsafe}
 return Report{Schema:ReportSchema,Mode:mode,BundleSHA256:bundleSHA,
  IncidentHeadSHA256:head,ManifestSHA256:manifestSHA,Incidents:len(chain),
  ReversibleRepairCandidates:len(batch.Repairs),
  OriginalReconciliations:len(batch.Reconcile),
  ScientificSuccessorReviews:len(batch.Scientific),IntegrityBlocks:len(batch.Blocked),
  VerifiedScientificCycles:0,OutboxIDs:ids},nil
}
// Run creates a NEW write-once shadow batch directory, never a mutable queue.
// A partial write is left for independent reconciliation: there is no retry
// of uncertain write results, nor any action against original experiments.
func Run(root string,req Request)(Report,error){
 if !allowedRoot(root){return Report{},ErrUnsafe}
 _,items,chain,batch,err:=evaluate(req)
 if err!=nil{return Report{},err}
 if len(chain)==0{return Report{},ErrUnsafe} // no invented success or empty diagnosis
 if err=os.Mkdir(root,0700);err!=nil{return Report{},errors.Join(ErrUnsafe,err)}
 bundle:=bundleOf(req)
 if err=writeOnce(filepath.Join(root,"witnessed-bundle.v1.json"),bundle);err!=nil{return Report{},err}
 if err=watchdog.ExportIncidentChain(root,chain);err!=nil{return Report{},err}
 manifest,err:=watchdog.SealRecoveryManifest(root,chain,items)
 if err!=nil{return Report{},err}
 ids:=[]string{}
 if len(batch.Repairs)>0{
  outbox:=filepath.Join(root,"outbox")
  if err=os.Mkdir(outbox,0700);err!=nil{return Report{},err}
  if _,err=shadowbridge.Stage(filepath.Join(root,"shadow-recovery-"+manifest.ManifestSHA256+".json"),outbox,manifest,chain);err!=nil{return Report{},err}
  ids,err=sortedOutboxIDs(outbox);if err!=nil{return Report{},err}
 }
 report,err:=reportFor(bundle,chain,batch,manifest.ManifestSHA256,ids)
 if err!=nil{return Report{},err}
 if err=writeOnce(filepath.Join(root,"shadow-report.v1.json"),report);err!=nil{return Report{},err}
 // Verify using caller-provisioned pins, not keys learned from the archive.
 observed,err:=Verify(root,req.WitnessPins,req.ReviewerPins)
 if err!=nil||!reflect.DeepEqual(report,observed){return Report{},ErrUnsafe}
 return report,nil
}
// Verify is a read-only restart check using EXTERNAL, independently provisioned
// pins. The archive may store public keys but cannot establish its own trust.
func Verify(root string,witnessPins []lanewitness.Pinned,reviewerPins []lanereview.ReviewerPin)(Report,error){
 if !allowedRoot(root){return Report{},ErrUnsafe}
 var b Bundle
 if err:=readCanonical(filepath.Join(root,"witnessed-bundle.v1.json"),&b);err!=nil||b.Schema!=BundleSchema{return Report{},ErrUnsafe}
 if !reflect.DeepEqual(b.WitnessPins,witnessPins)||!reflect.DeepEqual(b.ReviewerPins,reviewerPins){return Report{},ErrUnsafe}
 _,_,expectedChain,batch,err:=evaluate(Request{NowUnix:b.NowUnix,Witnesses:b.Witnesses,WitnessPins:witnessPins,
  Reviews:b.Reviews,ReviewerPins:reviewerPins})
 if err!=nil||len(expectedChain)==0{return Report{},ErrUnsafe}
 chain,_,err:=watchdog.ImportIncidentChain(root)
 if err!=nil||!reflect.DeepEqual(chain,expectedChain){return Report{},ErrUnsafe}
 var report Report
 if err=readCanonical(filepath.Join(root,"shadow-report.v1.json"),&report);err!=nil{return Report{},ErrUnsafe}
 var manifest watchdog.RecoveryManifest
 if err=readCanonical(filepath.Join(root,"shadow-recovery-"+report.ManifestSHA256+".json"),&manifest);err!=nil{return Report{},ErrUnsafe}
 if _,err=shadowbridge.Prepare(manifest,chain);err!=nil{return Report{},ErrUnsafe}
 if !reflect.DeepEqual(manifest.Repairs,batch.Repairs)||
  !reflect.DeepEqual(manifest.Reconcile,batch.Reconcile)||
  !reflect.DeepEqual(manifest.Scientific,batch.Scientific)||
  !reflect.DeepEqual(manifest.Blocked,batch.Blocked){return Report{},ErrUnsafe}
 ids:=[]string{}
 if len(batch.Repairs)>0{
  staged,err:=shadowoutbox.Load(filepath.Join(root,"outbox"))
  if err!=nil||len(staged)!=len(batch.Repairs){return Report{},ErrUnsafe}
  ids,err=sortedOutboxIDs(filepath.Join(root,"outbox"));if err!=nil{return Report{},ErrUnsafe}
  intended,err:=shadowbridge.Prepare(manifest,chain);if err!=nil{return Report{},ErrUnsafe}
  used:=make([]bool,len(staged))
  for _,want:=range intended{
   matched:=false
   for i,got:=range staged{
    if !used[i]&&reflect.DeepEqual(got,want){used[i]=true;matched=true;break}
   }
   if !matched{return Report{},ErrUnsafe}
  }
 }
 expected,err:=reportFor(b,chain,batch,manifest.ManifestSHA256,ids)
 if err!=nil||!reflect.DeepEqual(expected,report){return Report{},ErrUnsafe}
 // The root contains only the immutable proof, chain, report, manifest and
 // optional read-only-recovery outbox. Unexpected records fail closed.
 entries,err:=os.ReadDir(root);if err!=nil{return Report{},ErrUnsafe}
 permitted:=map[string]bool{"witnessed-bundle.v1.json":true,"shadow-chain.v1.json":true,
  "shadow-report.v1.json":true,"shadow-recovery-"+manifest.ManifestSHA256+".json":true}
 if len(batch.Repairs)>0{permitted["outbox"]=true}
 if len(entries)!=len(permitted){return Report{},ErrUnsafe}
 for _,entry:=range entries{
  if !permitted[entry.Name()]{return Report{},ErrUnsafe}
  if entry.Name()=="outbox" {if !entry.IsDir()||entry.Type()&os.ModeSymlink!=0{return Report{},ErrUnsafe}
  }else if !entry.Type().IsRegular(){return Report{},ErrUnsafe}
 }
 return report,nil
}
