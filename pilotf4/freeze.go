package pilotf4

import (
 "crypto/sha1"
 "encoding/hex"
 "encoding/json"
 "fmt"
 "os"
 "errors"
)
const FreezeBlob="76b940cae65c2800100bf1c589949bfa17ad3258"
var ErrInvalid=errors.New("F4_INVALID")
type Frozen struct{
 Schema string `json:"schema"`
 Generation string `json:"generation"`
 Class string `json:"class"`
 Wingless struct{ Cases int `json:"preregistered_cases"`;Context int `json:"contexts"`;Roles int `json:"roles_per_context"`;Capacity int `json:"capacity_entries"`;BaselineCapacity int `json:"baseline_capacity_entries"`;Train []int `json:"training_seeds"`;Hold []int `json:"heldout_seeds"` } `json:"wingless"`
 Yggdrasil struct{ Cases int `json:"preregistered_cases"`;Slots int `json:"slots_total"`;Protected int `json:"protected_slots"`;Recent int `json:"recency_slots"`;Baseline int `json:"baseline_slots"`;Bursts int `json:"bursts"`;Train []int `json:"training_seeds"`;Hold []int `json:"heldout_seeds"` } `json:"yggdrasil"`
}
func LoadFrozen(path string)(Frozen,error){
 var z Frozen
 b,err:=os.ReadFile(path);if err!=nil||len(b)==0||len(b)>16384{return z,ErrInvalid}
 h:=sha1.New();_,_=fmt.Fprintf(h,"blob %d\x00",len(b));_,_=h.Write(b)
 if hex.EncodeToString(h.Sum(nil))!=FreezeBlob{return z,ErrInvalid}
 if json.Unmarshal(b,&z)!=nil||z.Schema!="forge.f4.preregistered.v1"||z.Generation!="F4"||z.Class!="SYNTHETIC_ONLY"{return Frozen{},ErrInvalid}
 if z.Wingless.Cases!=960||z.Wingless.Context!=2||z.Wingless.Roles!=5||
  z.Wingless.Capacity!=10||z.Wingless.BaselineCapacity!=10||
  z.Yggdrasil.Cases!=160||z.Yggdrasil.Slots!=12||
  z.Yggdrasil.Protected!=6||z.Yggdrasil.Recent!=6||
  z.Yggdrasil.Baseline!=12||z.Yggdrasil.Bursts!=5{return Frozen{},ErrInvalid}
 if len(z.Wingless.Train)!=4||len(z.Wingless.Hold)!=4||len(z.Yggdrasil.Train)!=8||len(z.Yggdrasil.Hold)!=8{return Frozen{},ErrInvalid}
 seen:=map[int]bool{}
 for _,cohort:=range [][]int{z.Wingless.Train,z.Wingless.Hold,z.Yggdrasil.Train,z.Yggdrasil.Hold}{
  for _,seed:=range cohort{if seen[seed]||seed<1{return Frozen{},ErrInvalid};seen[seed]=true}
 }
 return z,nil
}
