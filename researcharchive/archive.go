// Package researcharchive binds independently collected real research ZIP
// artifacts to their original repository/run/source identities. No data here
// is an authorization or an independently qualified scientific result.
package researcharchive

import (
 "archive/zip"
 "bytes"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "io"
 "path"
 "sort"
 "strings"
)

const ManifestSchema="forge.research-archive.frozen-cohort.v1"
const ReportSchema="forge.research-archive.original-byte-inventory.v1"
const MaxZipBytes=4<<20
var ErrBlocked=errors.New("FORGE_ORIGINAL_ARCHIVE_PROVENANCE_OR_CUSTODY_UNVERIFIED")
type Entry struct{
 Lane string `json:"lane"`
 Experiment string `json:"experiment"`
 Repository string `json:"repository"`
 RunID uint64 `json:"run_id"`
 HeadSHA string `json:"head_sha"`
 WorkflowPath string `json:"workflow_path"`
 ArtifactID uint64 `json:"artifact_id"`
 ArtifactName string `json:"artifact_name"`
 ArchiveSHA256 string `json:"archive_sha256"`
}
type Manifest struct {
 Schema string `json:"schema"`
 Entries []Entry `json:"entries"`
}
type Observation struct{
 Lane string `json:"lane"`
 Experiment string `json:"experiment"`
 OriginalRunID uint64 `json:"original_run_id"`
 OriginalHeadSHA string `json:"original_head_sha"`
 ArtifactID uint64 `json:"artifact_id"`
 ArchiveSHA256 string `json:"archive_sha256"`
 Files []string `json:"files"`
 ArchivalIntegrityVerified bool `json:"archival_integrity_verified"`
 ScientificClassification string `json:"scientific_classification"`
 PreregistrationVerified bool `json:"preregistration_verified"`
 FirstUseReconciled bool `json:"first_use_reconciled"`
 ScientificAccepted bool `json:"scientific_accepted"`
}
type Report struct{
 Schema string `json:"schema"`
 Mode string `json:"mode"`
 ManifestSHA256 string `json:"manifest_sha256"`
 ArchiveCount int `json:"archive_count"`
 WinglessCount int `json:"wingless_count"`
 YggdrasilCount int `json:"yggdrasil_count"`
 Observations []Observation `json:"observations"`
 OriginalExecutionAuthorized bool `json:"original_execution_authorized"`
 CompleteCKBCustody bool `json:"complete_ckb_custody"`
 ScientificAccepted bool `json:"scientific_accepted"`
 AcceptedRefMutation bool `json:"accepted_ref_mutation"`
}
func goodHex(s string,n int)bool{
 if len(s)!=n{return false}
 for _,c:=range s{if !(c>='0'&&c<='9'||c>='a'&&c<='f'){return false}}
 return true
}
func simple(s string)bool{
 if len(s)==0||len(s)>160{return false}
 for _,c:=range s{
  if !(c>='a'&&c<='z'||c>='A'&&c<='Z'||c>='0'&&c<='9'||c=='-'||c=='_'||c=='.'){return false}
 }
 return s!="."&&s!=".."
}
func valid(e Entry)bool{
 if e.Lane!="Wingless"&&e.Lane!="Yggdrasil"{return false}
 return e.Repository=="spoonman136668-ai/"+e.Lane&&
  e.RunID>0&&e.ArtifactID>0&&goodHex(e.HeadSHA,40)&&
  goodHex(e.ArchiveSHA256,64)&&simple(e.Experiment)&&simple(e.ArtifactName)&&
  strings.HasPrefix(e.WorkflowPath,".github/workflows/qualify-")&&
  strings.HasSuffix(e.WorkflowPath,".yml")&&len(e.WorkflowPath)<200&&
  !strings.Contains(e.WorkflowPath,"..")&&
  !strings.Contains(e.WorkflowPath,"\\")
}
func SHA(b []byte)string{
 sum:=sha256.Sum256(b)
 return hex.EncodeToString(sum[:])
}
func LoadManifest(raw []byte)(Manifest,error){
 var m Manifest
 if len(raw)==0||len(raw)>16384{return m,ErrBlocked}
 d:=json.NewDecoder(bytes.NewReader(raw));d.DisallowUnknownFields()
 if d.Decode(&m)!=nil||d.Decode(new(any))!=io.EOF{return Manifest{},ErrBlocked}
 enc,err:=json.Marshal(m)
 if err!=nil||!bytes.Equal(raw,append(enc,'\n'))||
  m.Schema!=ManifestSchema||len(m.Entries)<2||len(m.Entries)>24{
  return Manifest{},ErrBlocked
 }
 runs:=map[uint64]bool{}
 artifacts:=map[uint64]bool{}
 candidates:=map[string]bool{}
 wingless,yggdrasil:=0,0
 prev:=""
 for _,e:=range m.Entries{
  if !valid(e)||runs[e.RunID]||artifacts[e.ArtifactID]||
   candidates[e.Lane+":"+e.Experiment]{return Manifest{},ErrBlocked}
  key:=e.Lane+":"+e.Experiment
  if prev!=""&&key<=prev{return Manifest{},ErrBlocked}
  prev=key;runs[e.RunID]=true;artifacts[e.ArtifactID]=true;candidates[key]=true
  if e.Lane=="Wingless"{wingless++}else{yggdrasil++}
 }
 if wingless==0||yggdrasil==0{return Manifest{},ErrBlocked}
 return m,nil
}
type sourceRun struct{
 ID uint64 `json:"id"`
 RunAttempt int `json:"run_attempt"`
 HeadSHA string `json:"head_sha"`
 Path string `json:"path"`
 Status string `json:"status"`
 Conclusion string `json:"conclusion"`
 Repository struct{FullName string `json:"full_name"`} `json:"repository"`
 HeadRepository *struct{FullName string `json:"full_name"`} `json:"head_repository"`
}
type sourceArtifact struct {
 ID uint64 `json:"id"`
 Name string `json:"name"`
 Expired bool `json:"expired"`
 Digest string `json:"digest"`
 Size uint64 `json:"size_in_bytes"`
 WorkflowRun struct {
  ID uint64 `json:"id"`
  HeadSHA string `json:"head_sha"`
 } `json:"workflow_run"`
}
// GitHub metadata is untrusted input. The standard JSON decoder silently
// resolves duplicate object keys (including case-insensitive struct aliases)
// by letting later values overwrite earlier identities. Reject ambiguity at
// EVERY nesting level before decoding run/artifact identity or custody.
func unambiguousJSON(raw []byte)bool{
 d:=json.NewDecoder(bytes.NewReader(raw))
 var value func(int)bool
 value=func(depth int)bool{
  if depth>48{return false}
  token,err:=d.Token()
  if err!=nil{return false}
  delimiter,ok:=token.(json.Delim)
  if !ok{return true}
  if delimiter!='{'&&delimiter!='['{return false}
  seen:=map[string]bool{}
  for d.More(){
   if delimiter=='{'{
    key,err:=d.Token()
    if err!=nil{return false}
    name,ok:=key.(string)
    if !ok||len(name)==0||len(name)>256{return false}
    folded:=strings.ToLower(name)
    if seen[folded]{return false}
    seen[folded]=true
   }
   if !value(depth+1){return false}
  }
  end,err:=d.Token()
  return err==nil&&end==json.Delim(map[json.Delim]rune{'{':'}','[':']'}[delimiter])
 }
 if !value(0){return false}
 _,err:=d.Token()
 return errors.Is(err,io.EOF)
}
func decode(raw []byte,dest any)error{
 if len(raw)==0||len(raw)>2<<20||!unambiguousJSON(raw){return ErrBlocked}
 d:=json.NewDecoder(bytes.NewReader(raw))
 if d.Decode(dest)!=nil||d.Decode(new(any))!=io.EOF{return ErrBlocked}
 return nil
}
func Verify(e Entry,runRaw,artifactRaw,zipRaw []byte)(Observation,error){
 var zero Observation
 if !valid(e)||len(zipRaw)==0||len(zipRaw)>MaxZipBytes||
  SHA(zipRaw)!=e.ArchiveSHA256{return zero,ErrBlocked}
 var run sourceRun
 if decode(runRaw,&run)!=nil||run.ID!=e.RunID||
  run.RunAttempt!=1||run.HeadSHA!=e.HeadSHA||
  run.Path!=e.WorkflowPath||run.Status!="completed"||
  run.Conclusion!="success"||run.Repository.FullName!=e.Repository||
  run.HeadRepository==nil||run.HeadRepository.FullName!=e.Repository{
  return zero,ErrBlocked
 }
 var artifact sourceArtifact
 if decode(artifactRaw,&artifact)!=nil||artifact.ID!=e.ArtifactID||
  artifact.Name!=e.ArtifactName||artifact.Expired||
  artifact.Size==0||artifact.Size>MaxZipBytes||
  artifact.Digest!="sha256:"+e.ArchiveSHA256||
  artifact.WorkflowRun.ID!=e.RunID||artifact.WorkflowRun.HeadSHA!=e.HeadSHA{
  return zero,ErrBlocked
 }
 z,err:=zip.NewReader(bytes.NewReader(zipRaw),int64(len(zipRaw)))
 if err!=nil||len(z.File)==0||len(z.File)>24{return zero,ErrBlocked}
 names:=make([]string,0,len(z.File))
 seen:=map[string]bool{}
 var total uint64
 for _,f:=range z.File{
  n:=f.Name
  if !simple(n)||path.Base(n)!=n||seen[n]||
   f.FileInfo().Mode().IsRegular()==false||
   f.UncompressedSize64==0||f.UncompressedSize64>MaxZipBytes||
   total>MaxZipBytes-f.UncompressedSize64||
   (f.Method!=zip.Store&&f.Method!=zip.Deflate){return zero,ErrBlocked}
  total+=f.UncompressedSize64;seen[n]=true
  rd,err:=f.Open()
  if err!=nil{return zero,ErrBlocked}
  read,err:=io.Copy(io.Discard,io.LimitReader(rd,int64(f.UncompressedSize64)+1))
  closed:=rd.Close()
  if err!=nil||closed!=nil||read!=int64(f.UncompressedSize64){return zero,ErrBlocked}
  names=append(names,n)
 }
 sort.Strings(names)
 return Observation{
  Lane:e.Lane,Experiment:e.Experiment,OriginalRunID:e.RunID,
  OriginalHeadSHA:e.HeadSHA,ArtifactID:e.ArtifactID,
  ArchiveSHA256:e.ArchiveSHA256,Files:names,ArchivalIntegrityVerified:true,
  ScientificClassification:"UNQUALIFIED_ORIGINAL_EVIDENCE_PRESERVED",
 },nil
}
// Collect is an observational-only join. The caller independently fetches
// each exact original run, artifact metadata and archived bytes.
func Collect(manifestRaw []byte,source func(Entry)([]byte,[]byte,[]byte,error))(Report,error){
 var zero Report
 manifest,err:=LoadManifest(manifestRaw)
 if err!=nil||source==nil{return zero,ErrBlocked}
 out:=Report{Schema:ReportSchema,
  Mode:"ORIGINAL_ARCHIVE_BYTE_PRESERVATION_NOT_SCIENTIFIC_CUSTODY",
  ManifestSHA256:SHA(manifestRaw),Observations:make([]Observation,0,len(manifest.Entries))}
 for _,e:=range manifest.Entries{
  run,artifact,zipData,err:=source(e)
  if err!=nil{return zero,ErrBlocked}
  item,err:=Verify(e,run,artifact,zipData)
  if err!=nil{return zero,ErrBlocked}
  out.Observations=append(out.Observations,item)
  if e.Lane=="Wingless"{out.WinglessCount++}else{out.YggdrasilCount++}
 }
 out.ArchiveCount=len(out.Observations)
 return out,nil
}
