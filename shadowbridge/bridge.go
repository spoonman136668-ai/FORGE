// Package shadowbridge connects sealed shadow repair manifests to an
// inactive, immutable recovery outbox. It cannot run repairs or science.
package shadowbridge
import (
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "os"
 "path/filepath"
 "github.com/spoonman136668-ai/forge/shadowoutbox"
 "github.com/spoonman136668-ai/forge/watchdog"
)
var ErrUnsafe=errors.New("FORGE_SHADOW_BRIDGE_NOT_AUTHENTICATED")
func hash(s string)bool{
 if len(s)!=64{return false}
 for _,v:=range s{if !(v>='0'&&v<='9'||v>='a'&&v<='f'){return false}}
 return true
}
// Prepare uses an exact archived manifest SHA and its immutable incident
// ancestry. Only pre-first-use, requalification-required repair intents
// are eligible. There is no general-purpose runner interface.
func Prepare(m watchdog.RecoveryManifest, chain []watchdog.DurableIncident)([]shadowoutbox.Entry,error){
 if m.Schema!="forge.shadow.recovery-manifest.v1"||!hash(m.ManifestSHA256)||
  !hash(m.IncidentChainHeadSHA256){return nil,ErrUnsafe}
 head,err:=watchdog.VerifyIncidentChain(chain)
 if err!=nil||head!=m.IncidentChainHeadSHA256{return nil,ErrUnsafe}
 // Hash the exact manifest content excluding its content-address identity.
 candidate:=m;candidate.ManifestSHA256=""
 b,err:=json.Marshal(candidate);if err!=nil{return nil,ErrUnsafe}
 d:=sha256.Sum256(append([]byte("FORGE-SHADOW-RECOVERY-MANIFEST-V1\n"),b...))
 if hex.EncodeToString(d[:])!=m.ManifestSHA256{return nil,ErrUnsafe}
 authenticated:=map[string]watchdog.Incident{}
 for _,c:=range chain{authenticated[watchdog.IncidentKey(c.Incident)]=c.Incident}
 used:=map[string]bool{}
 out:=make([]shadowoutbox.Entry,0,len(m.Repairs))
 for _,r:=range m.Repairs{
  i,ok:=authenticated[r.IncidentKey]
  if !ok||used[r.IncidentKey]||i.FirstUseRisk||
   i.Lane!=r.Lane||i.OriginalExperimentID!=r.ExperimentID||
   i.JournalHeadSHA256!=r.FrozenHeadSHA256||i.OwnerEpoch!=r.OwnerEpoch||
   !r.RequiresIndependentRequalification||r.Scope==""{return nil,ErrUnsafe}
  used[r.IncidentKey]=true
  k:=sha256.Sum256([]byte("FORGE-SHADOW-INCIDENT-KEY-V1\n"+r.IncidentKey))
  out=append(out,shadowoutbox.Entry{Schema:shadowoutbox.Schema,Lane:r.Lane,
   OriginalID:r.ExperimentID,IncidentSHA256:hex.EncodeToString(k[:]),
   RecoveryManifestSHA256:m.ManifestSHA256,Scope:r.Scope,
   FirstUseRisk:false,RequiresRequalification:true})
 }
 for _,group:=range [][]watchdog.Incident{m.Reconcile,m.Scientific,m.Blocked}{
  for _,i:=range group{key:=watchdog.IncidentKey(i);if _,ok:=authenticated[key];!ok||used[key]{return nil,ErrUnsafe};used[key]=true}
 }
 return out,nil
}
// Stage writes only to the inactive local outbox after re-verifying the
// persisted, canonical manifest bytes. A partial failure is not dispatched.
func Stage(manifestPath,dir string,m watchdog.RecoveryManifest,chain []watchdog.DurableIncident)([]string,error){
 if !filepath.IsAbs(manifestPath)||!filepath.IsAbs(dir){return nil,ErrUnsafe}
 raw,err:=os.ReadFile(manifestPath);if err!=nil||len(raw)>1<<20{return nil,ErrUnsafe}
 b,err:=json.Marshal(m)
 if err!=nil||string(raw)!=string(append(b,'\n'))||filepath.Base(manifestPath)!="shadow-recovery-"+m.ManifestSHA256+".json"{return nil,ErrUnsafe}
 entries,err:=Prepare(m,chain);if err!=nil{return nil,err}
 ids:=[]string{}
 for _,e:=range entries{
  id,err:=shadowoutbox.Enqueue(dir,e)
  if err!=nil{return nil,errors.Join(ErrUnsafe,err)}
  ids=append(ids,id)
 }
 return ids,nil
}
