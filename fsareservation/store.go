// Package fsareservation provides a server-side durable one-shot reservation
// primitive. It is NOT an independently authenticated FSA service: deployment,
// operator-pinned identity, private network authentication, monotonic journal
// integration and crash/fault qualification remain mandatory.
package fsareservation

import (
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "fmt"
 "os"
 "path/filepath"

 "github.com/spoonman136668-ai/forge/startrecovery"
)

var (
 ErrUnprovisioned=errors.New("FORGE_FSA_STORE_UNPROVISIONED")
 ErrConsumed=errors.New("FORGE_FSA_COHORT_ALREADY_RESERVED")
 ErrIndeterminate=errors.New("FORGE_FSA_RESERVATION_INDETERMINATE_NO_RETRY")
 ErrInvalid=errors.New("FORGE_FSA_RESERVATION_INVALID")
)

// Store is opened by the separately trusted FSA process, never by a research
// worker. The root must already exist on an independently provisioned volume.
type Store struct{root string}
func Open(root string)(*Store,error){
 if !filepath.IsAbs(root){return nil,ErrUnprovisioned}
 fi,err:=os.Lstat(root)
 if err!=nil||!fi.IsDir()||fi.Mode()&os.ModeSymlink!=0{return nil,ErrUnprovisioned}
 return &Store{root:root},nil
}
type record struct {
 Schema string `json:"schema"`
 Intent startrecovery.Intent `json:"intent"`
 SHA256 string `json:"sha256"`
}
func valid(i startrecovery.Intent)bool{
 _,err:=startrecovery.ReconcileIntent(i,startrecovery.Observation{
  Intent:i,Status:startrecovery.NoReservation,IndependentlyAuthenticated:true,
 })
 return err==nil
}
func key(i startrecovery.Intent)string{
 // Cohorts are global across Wingless/Yggdrasil: different experiments cannot
 // silently reuse an exhausted cohort.
 return i.CohortSHA256
}
func digest(i startrecovery.Intent)(string,error){
 b,err:=json.Marshal(i);if err!=nil{return "",err}
 h:=sha256.Sum256(append([]byte("FORGE-FSA-RESERVATION-V1\n"),b...))
 return hex.EncodeToString(h[:]),nil
}
// Reserve creates one immutable cohort claim with O_EXCL. A successful create
// followed by an fsync error is *indeterminate*: never remove/retry the claim.
// Atomic create works across cooperating processes on a local filesystem.
// This primitive alone does NOT solve multi-node linearizability or identity.
func (s *Store) Reserve(i startrecovery.Intent)error{
 if s==nil||!valid(i){return ErrInvalid}
 d,err:=digest(i);if err!=nil{return ErrInvalid}
 r:=record{Schema:"forge.fsa.reservation.v1",Intent:i,SHA256:d}
 data,err:=json.Marshal(r);if err!=nil{return ErrInvalid}
 name:=filepath.Join(s.root,key(i)+".json")
 f,err:=os.OpenFile(name,os.O_WRONLY|os.O_CREATE|os.O_EXCL,0600)
 if errors.Is(err,os.ErrExist){return ErrConsumed}
 if err!=nil{return fmt.Errorf("%w: create: %v",ErrIndeterminate,err)}
 _,werr:=f.Write(append(data,'\n'))
 if werr==nil{werr=f.Sync()}
 cerr:=f.Close()
 if werr!=nil||cerr!=nil{return ErrIndeterminate}
 dir,err:=os.Open(s.root)
 if err!=nil{return ErrIndeterminate}
 serr:=dir.Sync()
 cerr=dir.Close()
 if serr!=nil||cerr!=nil{return ErrIndeterminate}
 return nil
}
// Inspect returns only local structural consistency, NEVER an authenticated
// no-reservation observation. A missing file may still represent an unobserved
// remote reservation; callers must use independent FSA trust.
func (s *Store) Inspect(i startrecovery.Intent)(bool,error){
 if s==nil||!valid(i){return false,ErrInvalid}
 b,err:=os.ReadFile(filepath.Join(s.root,key(i)+".json"))
 if errors.Is(err,os.ErrNotExist){return false,nil}
 if err!=nil{return false,ErrIndeterminate}
 var r record
 if json.Unmarshal(b,&r)!=nil||r.Schema!="forge.fsa.reservation.v1"{return true,ErrIndeterminate}
 d,err:=digest(r.Intent)
 if err!=nil||r.SHA256!=d||r.Intent.CohortSHA256!=i.CohortSHA256{return true,ErrIndeterminate}
 return true,nil
}
