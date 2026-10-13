// Package originalinventory validates exact bytes of externally identified
// ORIGINAL research artifacts without changing their scientific disposition
// or attributing execution authority to FORGE.
package originalinventory

import (
 "bytes"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "io"
 "regexp"
)

const Schema="forge.original-evidence-inventory.v1"
const ResultSchema="forge.original-evidence-observation.v1"
var ErrBlocked=errors.New("FORGE_ORIGINAL_EVIDENCE_UNVERIFIED_OR_DRIFT")
type Pin struct{
 Lane string `json:"lane"`
 Repo string `json:"repo"`
 RunID uint64 `json:"run_id"`
 CommitSHA string `json:"commit_sha"`
 ArtifactID uint64 `json:"artifact_id"`
 ArtifactName string `json:"artifact_name"`
 FileName string `json:"file_name"`
 RawSHA256 string `json:"raw_sha256"`
 ExpectedReportedClassification string `json:"expected_reported_classification"`
}
type Manifest struct{
 Schema string `json:"schema"`
 Pins []Pin `json:"pins"`
}
type Observation struct{
 Lane string `json:"lane"`
 Repo string `json:"repo"`
 RunID uint64 `json:"run_id"`
 CommitSHA string `json:"commit_sha"`
 ArtifactID uint64 `json:"artifact_id"`
 ArtifactName string `json:"artifact_name"`
 FileName string `json:"file_name"`
 RawSHA256 string `json:"raw_sha256"`
 ReportedClassification string `json:"reported_classification"`
 Preservation string `json:"preservation"`
 ModelCallsReported *int `json:"model_calls_reported,omitempty"`
 ScientificClassification string `json:"scientific_classification"`
 SourceBirthVerified bool `json:"source_birth_verified"`
 PreregistrationVerified bool `json:"preregistration_verified"`
 IndependentQualificationVerified bool `json:"independent_qualification_verified"`
 OriginalFirstUseReconciled bool `json:"original_first_use_reconciled"`
 ScientificAccepted bool `json:"scientific_accepted"`
}
type Report struct{
 Schema string `json:"schema"`
 Mode string `json:"mode"`
 ManifestSHA256 string `json:"manifest_sha256"`
 Wingless Observation `json:"wingless"`
 Yggdrasil Observation `json:"yggdrasil"`
 OriginalScientificExecutionsAuthorized bool `json:"original_scientific_executions_authorized"`
 AcceptedRefMutation bool `json:"accepted_ref_mutation"`
 CKBOriginalCustodyReconciled bool `json:"ckb_original_custody_reconciled"`
}
func hexText(s string,n int)bool{
 if len(s)!=n{return false}
 for _,ch:=range s{if !(ch>='0'&&ch<='9'||ch>='a'&&ch<='f'){return false}}
 return true
}
var simple=regexp.MustCompile(`^[A-Za-z0-9_.-]+$`)
func validPin(p Pin)bool{
 if p.Lane!="Wingless"&&p.Lane!="Yggdrasil"{return false}
 if p.Repo!="spoonman136668-ai/"+p.Lane||p.RunID==0||p.ArtifactID==0||
  !hexText(p.CommitSHA,40)||!hexText(p.RawSHA256,64)||
  len(p.ArtifactName)==0||len(p.ArtifactName)>120||
  len(p.FileName)<6||len(p.FileName)>120||
  !simple.MatchString(p.ArtifactName)||!simple.MatchString(p.FileName)||
  p.FileName[len(p.FileName)-5:]!=".json"||
  len(p.ExpectedReportedClassification)==0||len(p.ExpectedReportedClassification)>96{return false}
 for _,c:=range p.ExpectedReportedClassification{
  if !(c>='A'&&c<='Z'||c>='0'&&c<='9'||c=='_'){return false}
 }
 return true
}
func canonicalManifest(raw []byte)(Manifest,error){
 var m Manifest
 if len(raw)==0||len(raw)>8192{return m,ErrBlocked}
 dec:=json.NewDecoder(bytes.NewReader(raw));dec.DisallowUnknownFields()
 if dec.Decode(&m)!=nil||dec.Decode(new(any))!=io.EOF||
  m.Schema!=Schema||len(m.Pins)!=2{return Manifest{},ErrBlocked}
 canonical,err:=json.Marshal(m)
 if err!=nil||!bytes.Equal(bytes.TrimSuffix(raw,[]byte("\n")),canonical){
  return Manifest{},ErrBlocked
 }
 if !validPin(m.Pins[0])||!validPin(m.Pins[1])||
  m.Pins[0].Lane!="Wingless"||m.Pins[1].Lane!="Yggdrasil"||
  m.Pins[0].RunID==m.Pins[1].RunID||
  m.Pins[0].ArtifactID==m.Pins[1].ArtifactID||
  m.Pins[0].RawSHA256==m.Pins[1].RawSHA256{return Manifest{},ErrBlocked}
 return m,nil
}
func topLevel(raw []byte)(map[string]json.RawMessage,error){
 if len(raw)==0||len(raw)>1<<20{return nil,ErrBlocked}
 decoder:=json.NewDecoder(bytes.NewReader(raw))
 token,err:=decoder.Token()
 if err!=nil||token!=json.Delim('{'){return nil,ErrBlocked}
 out:=map[string]json.RawMessage{}
 for decoder.More(){
  keyToken,err:=decoder.Token()
  if err!=nil{return nil,ErrBlocked}
  key,ok:=keyToken.(string)
  if !ok||len(key)==0||len(key)>128{return nil,ErrBlocked}
  if _,exists:=out[key];exists{return nil,ErrBlocked}
  var val json.RawMessage
  if decoder.Decode(&val)!=nil{return nil,ErrBlocked}
  out[key]=val
 }
 token,err=decoder.Token()
 if err!=nil||token!=json.Delim('}'){return nil,ErrBlocked}
 if decoder.Decode(new(any))!=io.EOF{return nil,ErrBlocked}
 return out,nil
}
func parse(p Pin,raw []byte)(Observation,error){
 var zero Observation
 if !validPin(p){return zero,ErrBlocked}
 sum:=sha256.Sum256(raw)
 if hex.EncodeToString(sum[:])!=p.RawSHA256{return zero,ErrBlocked}
 fields,err:=topLevel(raw);if err!=nil{return zero,err}
 var classification string
 if json.Unmarshal(fields["classification"],&classification)!=nil||
  classification!=p.ExpectedReportedClassification{return zero,ErrBlocked}
 var calls *int
 if field,ok:=fields["model_calls"];ok{
  var n int
  if json.Unmarshal(field,&n)!=nil||n<0{return zero,ErrBlocked}
  calls=&n
 }
 preservation:="CLAIM_ONLY_UNQUALIFIED"
 if classification=="NO_BENEFIT"||classification=="NEGATIVE"||
  classification=="NO_IMPROVEMENT"{preservation="REPORTED_NEGATIVE_PRESERVED_UNQUALIFIED"}
 return Observation{Lane:p.Lane,Repo:p.Repo,RunID:p.RunID,
  CommitSHA:p.CommitSHA,ArtifactID:p.ArtifactID,ArtifactName:p.ArtifactName,
  FileName:p.FileName,RawSHA256:p.RawSHA256,
  ReportedClassification:classification,Preservation:preservation,
  ModelCallsReported:calls,
  ScientificClassification:"UNVERIFIED_REQUIRES_INDEPENDENT_ORIGINAL_CUSTODY"},nil
}
// Build checks ONLY original raw bytes against caller-pinned GitHub artifact
// identity and recorded classification. The caller MUST separately
// authenticate the manifest and the GitHub run/artifact association.
func Build(manifestRaw,winglessRaw,yggdrasilRaw []byte)(Report,error){
 var zero Report
 m,err:=canonicalManifest(manifestRaw)
 if err!=nil{return zero,err}
 w,err:=parse(m.Pins[0],winglessRaw)
 if err!=nil{return zero,err}
 y,err:=parse(m.Pins[1],yggdrasilRaw)
 if err!=nil{return zero,err}
 h:=sha256.Sum256(manifestRaw)
 return Report{Schema:ResultSchema,Mode:"OBSERVED_ORIGINAL_BYTES_NO_EXECUTION_OR_SCIENTIFIC_AUTHORITY",
  ManifestSHA256:hex.EncodeToString(h[:]),
  Wingless:w,Yggdrasil:y},nil
}
