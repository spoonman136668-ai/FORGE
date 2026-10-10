// Package mindcontext reads bounded, advisory records from a pinned private
// Mind-Palace GitHub commit. It performs no controller, queue, science or
// Mind-Palace writes. The caller provides an authenticated read-only source.
package mindcontext

import (
 "context"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "fmt"
 "strings"
)

const (
 BootstrapPath = ".ice/remote-bootstrap.json"
 CatalogPath = ".ice/remote-catalog.json"
 IndexPath = ".ice/remote-index.ndjson"
 BootstrapSchema = "mind-palace.remote-bootstrap.v1"
 CatalogSchema = "mind-palace.remote-catalog.v1"
 MaxRemoteBytes = 1048576
 MaxRecords = 24
 MaxStatementBytes = 1600
 MaxOutputBytes = 16384
)
type Source interface {
 ResolveMain(context.Context)(string,error)
 ReadAt(context.Context,string,string)([]byte,error)
}
type Range struct {
 StartLine int `json:"start_line"`
 EndLine int `json:"end_line"`
 Count int `json:"count"`
}
type recordSource struct {
 Type string `json:"type"`
 Ref string `json:"ref"`
}
type Record struct {
 ID string `json:"id"`
 Project *string `json:"project"`
 Kind string `json:"kind"`
 Status string `json:"status"`
 Importance string `json:"importance"`
 Statement string `json:"statement"`
 SourceRefs []recordSource `json:"source_refs"`
}
type Entry struct {
 ID string `json:"id"`
 Project string `json:"project"`
 Kind string `json:"kind"`
 Statement string `json:"statement"`
 SourceRefs []recordSource `json:"source_refs"`
}
type Result struct {
 Schema string `json:"schema"`
 PinnedCommit string `json:"pinned_commit"`
 RecordsSHA256 string `json:"records_sha256"`
 ContextSHA256 string `json:"context_sha256"`
 Entries []Entry `json:"entries"`
 Truncated bool `json:"truncated"`
 AdvisoryOnly bool `json:"advisory_only"`
}
type bootstrapDoc struct {
 Schema string `json:"schema"`
 Source struct { RecordsSHA256 string `json:"records_sha256"` } `json:"source"`
 RetrievalTransport string `json:"retrieval_transport"`
 RemoteCatalog string `json:"remote_catalog"`
 RemoteIndex string `json:"remote_index"`
}
type catalogDoc struct {
 Schema string `json:"schema"`
 Source struct { RecordsSHA256 string `json:"records_sha256"` } `json:"source"`
 Index string `json:"index"`
 ActiveRecordCount int `json:"active_record_count"`
 Projects map[string]Range `json:"projects"`
 RetrievalTransport string `json:"retrieval_transport"`
 ControlPlaneRequired bool `json:"control_plane_required"`
}
type Reader struct { Source Source }
func lowerHex(s string,n int)bool{
 if len(s)!=n{return false}
 for _,c:=range s{if !((c>='0'&&c<='9')||(c>='a'&&c<='f')){return false}}
 return true
}
func hash(b []byte)string{h:=sha256.Sum256(b);return hex.EncodeToString(h[:])}
func allowedProject(p string)bool{
 switch p{case "Wingless","Yggdrasil","Research":return true};return false
}
func readJSON[T any](ctx context.Context,src Source,pin,path string)(T,error){
 var empty T
 b,err:=src.ReadAt(ctx,pin,path)
 if err!=nil{return empty,fmt.Errorf("FORGE_MIND_FETCH_FAILED_%s: %w",path,err)}
 if len(b)==0||len(b)>MaxRemoteBytes{return empty,errors.New("FORGE_MIND_DOCUMENT_SIZE")}
 if err=json.Unmarshal(b,&empty);err!=nil{return empty,errors.New("FORGE_MIND_DOCUMENT_JSON_INVALID")}
 return empty,nil
}
func validRanges(cat catalogDoc,n int)bool{
 if n<1||n>25000||len(cat.Projects)==0||len(cat.Projects)>64{return false}
 claimed:=make([]bool,n+1)
 total:=0
 for _,v:=range cat.Projects{
  if v.StartLine<1||v.EndLine<v.StartLine||v.EndLine>n||v.Count!=v.EndLine-v.StartLine+1{return false}
  for k:=v.StartLine;k<=v.EndLine;k++{
   if claimed[k]{return false};claimed[k]=true
  }
  total+=v.Count
 }
 return total==n
}
func vetted(r Record,project string)(Entry,error){
 if len(r.ID)==0||len(r.ID)>180||strings.TrimSpace(r.ID)!=r.ID||len(r.Kind)==0||len(r.Kind)>50||len(r.Statement)==0||len(r.Statement)>MaxStatementBytes||strings.ContainsRune(r.Statement,0){
  return Entry{},errors.New("FORGE_MIND_RECORD_INVALID")
 }
 actual:="__global__"
 if r.Project!=nil{actual=*r.Project}
 if actual!=project{return Entry{},errors.New("FORGE_MIND_RECORD_PROJECT_MISMATCH")}
 switch r.Status{case "current","confirmed","observed":default:return Entry{},errors.New("FORGE_MIND_STATUS_NOT_ADMITTED")}
 if len(r.SourceRefs)==0||len(r.SourceRefs)>12{return Entry{},errors.New("FORGE_MIND_PROVENANCE_MISSING")}
 for _,s:=range r.SourceRefs{
  if s.Type==""||len(s.Type)>36||s.Ref==""||len(s.Ref)>512||strings.ContainsAny(s.Ref,"\r\n\x00") {return Entry{},errors.New("FORGE_MIND_SOURCE_REF_INVALID")}
 }
 return Entry{ID:r.ID,Project:actual,Kind:r.Kind,Statement:r.Statement,SourceRefs:r.SourceRefs},nil
}
// Read resolves main exactly once, pins every fetch to that immutable commit,
// and returns only allowed project context + mandatory global governance.
// The underlying GitHub API may transfer the full index; the output is bounded
// and the private bytes are never written by this package.
func (r Reader) Read(ctx context.Context,projects []string,maxEntries int)(Result,error){
 var zero Result
 if r.Source==nil||ctx==nil{return zero,errors.New("FORGE_MIND_SOURCE_MISSING")}
 if maxEntries<1||maxEntries>MaxRecords||len(projects)<1||len(projects)>3{return zero,errors.New("FORGE_MIND_QUERY_BOUNDS")}
 seen:=map[string]bool{}
 for _,p:=range projects{
  if !allowedProject(p)||seen[p]{return zero,errors.New("FORGE_MIND_PROJECT_NOT_ALLOWED")}
  seen[p]=true
 }
 pin,err:=r.Source.ResolveMain(ctx)
 if err!=nil||!lowerHex(pin,40){return zero,errors.New("FORGE_MIND_PIN_UNVERIFIED")}
 bootstrap,err:=readJSON[bootstrapDoc](ctx,r.Source,pin,BootstrapPath);if err!=nil{return zero,err}
 catalog,err:=readJSON[catalogDoc](ctx,r.Source,pin,CatalogPath);if err!=nil{return zero,err}
 if bootstrap.Schema!=BootstrapSchema||catalog.Schema!=CatalogSchema||
    bootstrap.RemoteCatalog!=CatalogPath||bootstrap.RemoteIndex!=IndexPath||catalog.Index!=IndexPath||
    bootstrap.RetrievalTransport!="direct-repository-read"||catalog.RetrievalTransport!="direct-repository-read"||
    catalog.ControlPlaneRequired||!lowerHex(bootstrap.Source.RecordsSHA256,64)||
    bootstrap.Source.RecordsSHA256!=catalog.Source.RecordsSHA256 {
  return zero,errors.New("FORGE_MIND_CONTRACT_OR_RECORDS_PIN_DRIFT")
 }
 raw,err:=r.Source.ReadAt(ctx,pin,IndexPath)
 if err!=nil{return zero,errors.New("FORGE_MIND_INDEX_FETCH_FAILED")}
 if len(raw)==0||len(raw)>MaxRemoteBytes||raw[len(raw)-1]!='\n'{return zero,errors.New("FORGE_MIND_INDEX_BOUNDS")}
 lines:=strings.Split(string(raw[:len(raw)-1]),"\n")
 if len(lines)!=catalog.ActiveRecordCount||!validRanges(catalog,len(lines)){return zero,errors.New("FORGE_MIND_RANGE_DRIFT")}
 grouped:=map[string][]Entry{}
 count:=0
 for _,p:=range append([]string{"__global__"},projects...){
  rangeInfo,ok:=catalog.Projects[p]
  if !ok{return zero,errors.New("FORGE_MIND_PROJECT_RANGE_MISSING")}
  for j:=rangeInfo.StartLine;j<=rangeInfo.EndLine;j++{
   line:=lines[j-1]
   if len(line)==0||len(line)>8192{return zero,errors.New("FORGE_MIND_LINE_SIZE")}
   var rec Record
   if err:=json.Unmarshal([]byte(line),&rec);err!=nil{return zero,errors.New("FORGE_MIND_RECORD_JSON_INVALID")}
   // Historical/non-current records are excluded from the generated index.
   // Fail closed instead of reinterpreting a stale generated record.
   entry,err:=vetted(rec,p);if err!=nil{return zero,err}
   grouped[p]=append(grouped[p],entry)
   count++
  }
 }
 out:=Result{Schema:"forge.mind-palace-context.v1",PinnedCommit:pin,RecordsSHA256:catalog.Source.RecordsSHA256,Entries:make([]Entry,0,maxEntries),AdvisoryOnly:true}
 for _,e:=range grouped["__global__"]{
  if len(out.Entries)==maxEntries{return zero,errors.New("FORGE_MIND_GOVERNANCE_EXCEEDS_BUDGET")}
  out.Entries=append(out.Entries,e)
 }
 // Round-robin project selection keeps both research missions visible.
 for n:=0;n<count;n++{
  madeProgress:=false
  for _,p:=range projects{
   if len(grouped[p])==0{continue}
   if len(out.Entries)==maxEntries{out.Truncated=true;break}
   out.Entries=append(out.Entries,grouped[p][0])
   grouped[p]=grouped[p][1:]
   madeProgress=true
  }
  if len(out.Entries)==maxEntries{
   for _,p:=range projects{if len(grouped[p])>0{out.Truncated=true}}
   break
  }
  if !madeProgress{break}
 }
 canonical,err:=json.Marshal(out.Entries)
 if err!=nil||len(canonical)>MaxOutputBytes{return zero,errors.New("FORGE_MIND_OUTPUT_BUDGET")}
 out.ContextSHA256=hash(canonical)
 return out,nil
}
