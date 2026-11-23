// Package researchfeed validates an untrusted six-lane evidence INDEX as a
// prospective FORGE advisory. It neither dispatches nor grants FSA acceptance.
package researchfeed

import (
 "bytes"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "io"
 "sort"
 "strings"
)

const (
 Schema="forge.research-six-lane-source-candidates.v1"
 PreviewSchema="forge.research-six-lane-preview.v1"
 MaxBytes=65536
 MaxEntries=60
)
var ErrBlocked=errors.New("FORGE_SIX_LANE_PROVENANCE_OR_AUTHORITY_UNVERIFIED")

type Candidate struct{
 Lane string `json:"lane"`
 ResearchID string `json:"research_id"`
 SourceRepo string `json:"source_repo"`
 SourceCommit string `json:"source_commit"`
 SourcePath string `json:"source_path"`
 ReportedSHA256 string `json:"reported_sha256"`
 Outcome string `json:"outcome"`
 EvidenceState string `json:"evidence_state"`
 // These may only ever be false in this untrusted transport.
 FirstUseCleared bool `json:"first_use_cleared"`
 ScientificAccepted bool `json:"scientific_accepted"`
 ExecuteRequested bool `json:"execute_requested"`
}
type Input struct{
 Schema string `json:"schema"`
 Candidates []Candidate `json:"candidates"`
}
type IndexEntry struct{
 Lane string `json:"lane"`
 ResearchID string `json:"research_id"`
 SourceRepo string `json:"source_repo"`
 SourceCommit string `json:"source_commit"`
 SourcePath string `json:"source_path"`
 ReportedSHA256 string `json:"reported_sha256"`
 Outcome string `json:"outcome"`
 EvidenceState string `json:"evidence_state"`
}
type Preview struct{
 Schema string `json:"schema"`
 InputSHA256 string `json:"input_sha256"`
 Entries []IndexEntry `json:"entries"`
 AdvisoryOnly bool `json:"advisory_only"`
 ScientificAccepted bool `json:"scientific_accepted"`
 ScientificFirstUseCleared bool `json:"scientific_first_use_cleared"`
 ExecutionAuthorized bool `json:"execution_authorized"`
 OriginalBytesAuthenticated bool `json:"original_bytes_authenticated"`
}

func hexLower(s string,n int)bool{
 if len(s)!=n{return false}
 for _,c:=range s{if (c<'0'||c>'9')&&(c<'a'||c>'f'){return false}}
 return true
}
func safeID(s string)bool{
 if len(s)==0||len(s)>100{return false}
 for _,c:=range s{
  if !((c>='a'&&c<='z')||(c>='A'&&c<='Z')||(c>='0'&&c<='9')||c=='-'||c=='_'||c=='.'){return false}
 }
 return !strings.Contains(s,"..")
}
func safePath(s string)bool{
 if len(s)==0||len(s)>512||strings.HasPrefix(s,"/")||strings.HasPrefix(s,".")||
 strings.Contains(s,"\\")||strings.Contains(s,"//")||strings.Contains(s,":")||strings.ContainsAny(s,"\r\n\x00"){return false}
 for _,x:=range strings.Split(s,"/"){if x==""||x=="."||x==".."{return false}}
 return true
}
func repoFor(lane,repo,path string)bool{
 switch lane{
 case "Wingless":return repo=="spoonman136668-ai/Wingless"&&
   (strings.HasPrefix(path,"research/")||strings.HasPrefix(path,"docs/"))
 case "Yggdrasil":return repo=="spoonman136668-ai/Yggdrasil"&&
   (strings.HasPrefix(path,"research/")||strings.HasPrefix(path,"docs/"))
 case "BIO","Optimizer Work","Mass Research","Language Research":
  return (repo=="spoonman136668-ai/Mind-Palace"&&strings.HasPrefix(path,"archive/research/"))||
   (repo=="spoonman136668-ai/FORGE"&&(strings.HasPrefix(path,"research/")||strings.HasPrefix(path,"docs/")))
 default:return false
 }
}
func valid(c Candidate)bool{
 if !safeID(c.ResearchID)||!safePath(c.SourcePath)||!repoFor(c.Lane,c.SourceRepo,c.SourcePath)||
   !hexLower(c.SourceCommit,40)||c.FirstUseCleared||c.ScientificAccepted||c.ExecuteRequested{return false}
 if c.ReportedSHA256!=""&&!hexLower(c.ReportedSHA256,64){return false}
 switch c.EvidenceState{case "SOURCE_POINTER_ONLY","REPORTED_BYTES_UNAUTHENTICATED","ORIGINAL_BYTES_CUSTODY_UNRESOLVED":default:return false}
 if c.EvidenceState=="REPORTED_BYTES_UNAUTHENTICATED"&&c.ReportedSHA256=="" {return false}
 switch c.Outcome{case "POSITIVE","NEGATIVE","MIXED","INVALID","INCONCLUSIVE","UNCLASSIFIED":default:return false}
 return true
}
// Rejects duplicate keys at every depth (including case variants) so a JSON
// decoder cannot silently replace a denied authority claim.
func uniqueKeys(raw []byte)bool{
 dec:=json.NewDecoder(bytes.NewReader(raw))
 var walk func(int)bool
 walk=func(depth int)bool{
  if depth>64{return false}
  token,err:=dec.Token()
  if err!=nil{return false}
  delim,ok:=token.(json.Delim)
  if !ok{return true}
  if delim!='{'&&delim!='['{return false}
  seen:=map[string]bool{}
  for dec.More(){
   if delim=='{'{
    k,err:=dec.Token();if err!=nil{return false}
    key,ok:=k.(string);if !ok||len(key)==0||len(key)>128{return false}
    key=strings.ToLower(key)
    if seen[key]{return false}
    seen[key]=true
   }
   if !walk(depth+1){return false}
  }
  end,err:=dec.Token();if err!=nil{return false}
  if delim=='{'{return end==json.Delim('}')}
  return end==json.Delim(']')
 }
 if !walk(0){return false}
 _,err:=dec.Token();return errors.Is(err,io.EOF)
}
// PreviewCandidates is purely functional. It does not touch existing FORGE
// researchintake, F139 dispatch, FSA custody, or any repository or API.
func PreviewCandidates(raw []byte)(Preview,error){
 var zero Preview
 if len(raw)==0||len(raw)>MaxBytes||!uniqueKeys(raw){return zero,ErrBlocked}
 d:=json.NewDecoder(bytes.NewReader(raw))
 d.DisallowUnknownFields()
 var input Input
 if d.Decode(&input)!=nil{return zero,ErrBlocked}
 var extra any
 if d.Decode(&extra)!=io.EOF{return zero,ErrBlocked}
 if input.Schema!=Schema||len(input.Candidates)==0||len(input.Candidates)>MaxEntries{return zero,ErrBlocked}
 seen:=make(map[string]bool,len(input.Candidates))
 output:=make([]IndexEntry,0,len(input.Candidates))
 for _,c:=range input.Candidates{
  if !valid(c){return zero,ErrBlocked}
  key:=c.Lane+":"+c.ResearchID
  if seen[key]{return zero,ErrBlocked}
  seen[key]=true
  output=append(output,IndexEntry{
   Lane:c.Lane,ResearchID:c.ResearchID,SourceRepo:c.SourceRepo,SourceCommit:c.SourceCommit,
   SourcePath:c.SourcePath,ReportedSHA256:c.ReportedSHA256,Outcome:c.Outcome,EvidenceState:c.EvidenceState,
  })
 }
 sort.Slice(output,func(i,j int)bool{
  if output[i].Lane!=output[j].Lane{return output[i].Lane<output[j].Lane}
  return output[i].ResearchID<output[j].ResearchID
 })
 hash:=sha256.Sum256(raw)
 return Preview{Schema:PreviewSchema,InputSHA256:hex.EncodeToString(hash[:]),
  Entries:output,AdvisoryOnly:true},nil
}
