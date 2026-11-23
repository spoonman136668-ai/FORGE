package watchdog

import (
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "os"
 "path/filepath"
)

// RecoveryManifest is the immutable shadow handoff between diagnosis and a
// separately qualified future executor. It never constitutes execution authority.
type RecoveryManifest struct {
 Schema string `json:"schema"`
 IncidentChainHeadSHA256 string `json:"incident_chain_head_sha256"`
 ManifestSHA256 string `json:"manifest_sha256"`
 Repairs []RepairIntent `json:"repairs"`
 Reconcile []Incident `json:"reconcile"`
 Scientific []Incident `json:"scientific"`
 Blocked []Incident `json:"blocked"`
}
const manifestSchema="forge.shadow.recovery-manifest.v1"
var ErrManifestUnsafe=errors.New("FORGE_RECOVERY_MANIFEST_NOT_VERIFIED")
func buildManifest(chain []DurableIncident, batch RecoveryBatch)(RecoveryManifest,error){
 head,err:=VerifyIncidentChain(chain);if err!=nil{return RecoveryManifest{},err}
 known:=map[string]bool{}
 for _,r:=range chain{known[IncidentKey(r.Incident)]=true}
 count:=0
 consumed:=map[string]bool{}
 for _,v:=range batch.Repairs{if consumed[v.IncidentKey]||!known[v.IncidentKey]||!v.RequiresIndependentRequalification{return RecoveryManifest{},ErrManifestUnsafe};consumed[v.IncidentKey]=true;count++}
 for _,group:=range [][]Incident{batch.Reconcile,batch.Scientific,batch.Blocked}{
  for _,v:=range group{if consumed[IncidentKey(v)]||!known[IncidentKey(v)]{return RecoveryManifest{},ErrManifestUnsafe};consumed[IncidentKey(v)]=true;count++}
 }
 if count==0||count>len(known){return RecoveryManifest{},ErrManifestUnsafe}
 m:=RecoveryManifest{Schema:manifestSchema,IncidentChainHeadSHA256:head,
  Repairs:batch.Repairs,Reconcile:batch.Reconcile,Scientific:batch.Scientific,Blocked:batch.Blocked}
 raw,err:=json.Marshal(m);if err!=nil{return RecoveryManifest{},err}
 digest:=sha256.Sum256(append([]byte("FORGE-SHADOW-RECOVERY-MANIFEST-V1\n"),raw...))
 m.ManifestSHA256=hex.EncodeToString(digest[:])
 return m,nil
}
// SealRecoveryManifest binds each proposed repair to a previously recorded
// hash-chained incident. A new evidence file is created exclusively;
// overwriting a sealed manifest is forbidden.
func SealRecoveryManifest(directory string,chain []DurableIncident,items []AssessedIncident)(RecoveryManifest,error){
 if directory==""||!filepath.IsAbs(directory){return RecoveryManifest{},ErrManifestUnsafe}
 persisted,head,err:=ImportIncidentChain(directory)
 if err!=nil{return RecoveryManifest{},err}
 suppliedHead,err:=VerifyIncidentChain(chain)
 if err!=nil||suppliedHead!=head||len(persisted)!=len(chain){return RecoveryManifest{},ErrManifestUnsafe}
 for i:=range chain{if persisted[i]!=chain[i]{return RecoveryManifest{},ErrManifestUnsafe}}
 batch,err:=PrepareRecoveryBatch(items);if err!=nil{return RecoveryManifest{},err}
 m,err:=buildManifest(persisted,batch);if err!=nil{return RecoveryManifest{},err}
 raw,err:=json.Marshal(m);if err!=nil{return RecoveryManifest{},err}
 f,err:=os.OpenFile(filepath.Join(directory,"shadow-recovery-"+m.ManifestSHA256+".json"),os.O_CREATE|os.O_EXCL|os.O_WRONLY,0600)
 if err!=nil{return RecoveryManifest{},errors.Join(ErrManifestUnsafe,err)}
 if _,err=f.Write(append(raw,'\n'));err!=nil{f.Close();return RecoveryManifest{},err}
 if err=f.Sync();err!=nil{f.Close();return RecoveryManifest{},err}
 if err=f.Close();err!=nil{return RecoveryManifest{},err}
 return m,nil
}
