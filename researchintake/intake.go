// Package researchintake is an offline, source-index-only observation ledger.
// It never authenticates scientific results, imports sealed data, or dispatches work.
package researchintake

import (
 "bytes"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "fmt"
 "io"
 "sort"
 "strconv"
 "strings"
 "time"
)

const SnapshotSchema = "forge.cross-lane-research-pr-snapshot.v1"
const ReportSchema = "forge.cross-lane-research-intake.v1"
const MaxSnapshotBytes = 256 << 10
const MaxReportBytes = 3 << 20
const MaxSnapshotEntries = 200
const MaxHistoryEntries = 4096
var ErrBlocked = errors.New("FORGE_RESEARCH_INTAKE_SOURCE_OR_PROVENANCE_UNVERIFIED")

type Source struct {
 Lane string `json:"lane"`
 PR uint64 `json:"pr"`
 HeadSHA string `json:"head_sha"`
 Title string `json:"title"`
 URL string `json:"url"`
 State string `json:"state"`
 Draft bool `json:"draft"`
 UpdatedAt string `json:"updated_at"`
}
type Snapshot struct {
 Schema string `json:"schema"`
 Sources []Source `json:"sources"`
}
type Record struct {
 Source
 SourceStatus string `json:"source_status"`
 ScientificOutcome string `json:"scientific_outcome"`
 OriginalFirstUseAuthenticated bool `json:"original_first_use_authenticated"`
 ScientificAccepted bool `json:"scientific_accepted"`
}
type Report struct {
 Schema string `json:"schema"`
 Mode string `json:"mode"`
 FirstSnapshotSHA256 string `json:"first_snapshot_sha256"`
 LastSnapshotSHA256 string `json:"last_snapshot_sha256"`
 TotalRevisions int `json:"total_revisions"`
 WinglessRevisions int `json:"wingless_revisions"`
 YggdrasilRevisions int `json:"yggdrasil_revisions"`
 HistoricalCompletenessVerified bool `json:"historical_completeness_verified"`
 NewScientificOriginalsExecuted bool `json:"new_scientific_originals_executed"`
 ScientificAccepted bool `json:"scientific_accepted"`
 FirstUseCleared bool `json:"first_use_cleared"`
 AuthorityMutated bool `json:"authority_mutated"`
 Revisions []Record `json:"revisions"`
 ReportSHA256 string `json:"report_sha256"`
}
func SHA(b []byte) string { s:=sha256.Sum256(b);return hex.EncodeToString(s[:]) }
func validHex(s string,n int)bool {if len(s)!=n{return false};for _,c:=range s {if !(c>='0'&&c<='9'||c>='a'&&c<='f'){return false}};return true}
func sourceKey(s Source)string{return s.Lane+":"+fmt.Sprintf("%010d",s.PR)+":"+s.HeadSHA}
func safeTitle(s string)bool {if len(s)==0||len(s)>200||strings.TrimSpace(s)!=s{return false};for _,c:=range s{if c<32||c==127||c==0xfffd{return false}};return true}
func validSource(s Source)bool {
 if s.Lane!="Wingless"&&s.Lane!="Yggdrasil"{return false}
 if s.PR==0||s.PR>99999999||!validHex(s.HeadSHA,40)||!safeTitle(s.Title) {return false}
 if s.URL!="https://github.com/spoonman136668-ai/"+s.Lane+"/pull/"+strconv.FormatUint(s.PR,10) {return false}
 if s.State!="open"&&s.State!="closed" {return false}
 when,err:=time.Parse(time.RFC3339,s.UpdatedAt);return err==nil&&when.Format(time.RFC3339)==s.UpdatedAt
}
// rejectAmbiguous rejects exact and case-insensitive duplicate keys at any depth,
// including ambiguities the Go JSON decoder would otherwise silently overwrite.
func rejectAmbiguous(b []byte) bool {
 d:=json.NewDecoder(bytes.NewReader(b))
 var read func(int)bool
 read=func(depth int)bool{
  if depth>64{return false}
  tok,err:=d.Token();if err!=nil{return false}
  start,ok:=tok.(json.Delim);if !ok{return true}
  if start!='{'&&start!='['{return false}
  seen:=map[string]bool{}
  for d.More(){
   if start=='{' {
    key,err:=d.Token();if err!=nil{return false}
    k,ok:=key.(string);if !ok||len(k)==0||len(k)>128{return false}
    folded:=strings.ToLower(k);if seen[folded]{return false};seen[folded]=true
   }
   if !read(depth+1){return false}
  }
  end,err:=d.Token();if err!=nil{return false}
  return end==json.Delim(map[json.Delim]rune{'{':'}','[':']'}[start])
 }
 if !read(0){return false}
 _,err:=d.Token();return errors.Is(err,io.EOF)
}
func decode(b []byte,max int,into any) error {
 if len(b)==0||len(b)>max||!rejectAmbiguous(b){return ErrBlocked}
 d:=json.NewDecoder(bytes.NewReader(b));d.DisallowUnknownFields()
 if d.Decode(into)!=nil{return ErrBlocked}
 var extra any;if d.Decode(&extra)!=io.EOF{return ErrBlocked};return nil
}
func reportHash(r Report)string{r.ReportSHA256="";b,_:=json.Marshal(r);return SHA(b)}
func validateReport(r Report)error {
 if r.Schema!=ReportSchema||r.Mode!="READ_ONLY_UNVERIFIED_PR_INDEX_NO_SCIENTIFIC_ACCEPTANCE"||
  !validHex(r.FirstSnapshotSHA256,64)||!validHex(r.LastSnapshotSHA256,64)||
  r.HistoricalCompletenessVerified||r.NewScientificOriginalsExecuted||r.ScientificAccepted||r.FirstUseCleared||r.AuthorityMutated||
  len(r.Revisions)==0||len(r.Revisions)>MaxHistoryEntries||r.TotalRevisions!=len(r.Revisions)||r.ReportSHA256!=reportHash(r){return ErrBlocked}
 wing,ygg:=0,0;last:=""
 for _,x:=range r.Revisions{
  k:=sourceKey(x.Source)
  if !validSource(x.Source)||x.SourceStatus!="OBSERVED_PR_METADATA_NOT_EVIDENCE"||
   x.ScientificOutcome!="NOT_CLASSIFIED"||x.OriginalFirstUseAuthenticated||x.ScientificAccepted||
   (last!=""&&k<=last){return ErrBlocked}
  last=k
  if x.Lane=="Wingless"{wing++}else{ygg++}
 }
 if r.WinglessRevisions!=wing||r.YggdrasilRevisions!=ygg{return ErrBlocked}
 return nil
}
// Ingest composes newly observed GitHub PR identities with a verified prior
// report. No PR title/status or successful CI result is interpreted as science.
// The caller owns archival transport and must independently authenticate evidence.
func Ingest(snapshotRaw,priorRaw []byte)(Report,error){
 var zero Report
 var snap Snapshot
 if decode(snapshotRaw,MaxSnapshotBytes,&snap)!=nil||snap.Schema!=SnapshotSchema||
  len(snap.Sources)==0||len(snap.Sources)>MaxSnapshotEntries{return zero,ErrBlocked}
 seen:=map[string]bool{}
 for _,s:=range snap.Sources{key:=sourceKey(s);if !validSource(s)||seen[key]{return zero,ErrBlocked};seen[key]=true}
 var out Report
 if len(priorRaw)>0{
  if decode(priorRaw,MaxReportBytes,&out)!=nil||validateReport(out)!=nil{return zero,ErrBlocked}
 }else{
  out=Report{Schema:ReportSchema,Mode:"READ_ONLY_UNVERIFIED_PR_INDEX_NO_SCIENTIFIC_ACCEPTANCE",FirstSnapshotSHA256:SHA(snapshotRaw),Revisions:[]Record{}}
 }
 existing:=map[string]bool{}
 for _,r:=range out.Revisions{existing[sourceKey(r.Source)]=true}
 changed:=false
 for _,s:=range snap.Sources{
  if existing[sourceKey(s)]{continue}
  if len(out.Revisions)>=MaxHistoryEntries{return zero,ErrBlocked}
  out.Revisions=append(out.Revisions,Record{Source:s,SourceStatus:"OBSERVED_PR_METADATA_NOT_EVIDENCE",ScientificOutcome:"NOT_CLASSIFIED"})
  changed=true
 }
 if !changed&&len(priorRaw)>0{return out,nil} // exact idempotence on replay
 sort.Slice(out.Revisions,func(i,j int)bool{return sourceKey(out.Revisions[i].Source)<sourceKey(out.Revisions[j].Source)})
 out.LastSnapshotSHA256=SHA(snapshotRaw)
 out.TotalRevisions=len(out.Revisions);out.WinglessRevisions=0;out.YggdrasilRevisions=0
 for _,r:=range out.Revisions{if r.Lane=="Wingless"{out.WinglessRevisions++}else{out.YggdrasilRevisions++}}
 out.ReportSHA256=reportHash(out)
 if validateReport(out)!=nil{return zero,ErrBlocked}
 return out,nil
}
