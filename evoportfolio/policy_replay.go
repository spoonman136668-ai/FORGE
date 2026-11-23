package evoportfolio

import (
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "sort"
)

var ErrPolicyReplay=errors.New("FORGE_POLICY_REPLAY_FROZEN_INVARIANT")
const PolicyReplaySchema="forge.policy-replay.frozen.v1"

// Observation is historical evidence only. Candidates must exist before any policy
// ranking. Each epoch's training/holdout split is frozen before replay.
type Observation struct {
 ID string `json:"id"`
 Family string `json:"family"`
 SourceSHA string `json:"source_sha"`
 Class string `json:"class"`
 Compute uint64 `json:"compute"`
 Epoch uint64 `json:"epoch"`
}
type PolicyFreeze struct {
 Schema string `json:"schema"`
 Lane string `json:"lane"`
 TrainingThrough uint64 `json:"training_through"`
 Candidates []Observation `json:"candidates"`
}
type PolicyScore struct {
 Name string `json:"name"`
 TrainingUtility int64 `json:"training_utility"`
 HoldoutUtility int64 `json:"holdout_utility"`
}
type PolicyReplay struct {
 Schema string `json:"schema"`
 FrozenSHA256 string `json:"frozen_sha256"`
 SelectedPolicy string `json:"selected_policy"`
 Scores []PolicyScore `json:"scores"`
 DispatchAuthorized bool `json:"dispatch_authorized"`
 AcceptedRefMutation bool `json:"accepted_ref_mutation"`
}

// ReplayPolicyDigest binds the complete immutable history and split identity.
func ReplayPolicyDigest(f PolicyFreeze) string {
 b,_:=json.Marshal(f); d:=sha256.Sum256(b); return hex.EncodeToString(d[:])
}
func outcomeUtility(class string) (int64,bool) {
 switch class {
 case "SUPPORTED":return 3,true
 case "MIXED":return 1,true
 case "NEGATIVE":return 0,true
 case "INVALID":return -2,true
 case "CONSUMED_INDETERMINATE":return -3,true
 }
 return 0,false
}

// ReplayFrozenPolicies compares prespecified ranking rules. Selection is based on
// training ONLY; held-out outcomes are reported afterward and never influence choice.
// It never makes a scientific execution or commits a new policy as accepted.
func ReplayFrozenPolicies(f PolicyFreeze,pin string)(PolicyReplay,error){
 var empty PolicyReplay
 if f.Schema!=PolicyReplaySchema||(f.Lane!="Wingless"&&f.Lane!="Yggdrasil")||
  f.TrainingThrough<1||len(f.Candidates)<4||len(f.Candidates)>160||
  ReplayPolicyDigest(f)!=pin{return empty,ErrPolicyReplay}
 ids:=map[string]bool{}
 hasTrain,hasHeld:=false,false
 for _,o:=range f.Candidates {
  if !validID(o.ID)||!validID(o.Family)||!isHex(o.SourceSHA,40)||
   o.Epoch<1||o.Compute<1||o.Compute>1000000||ids[o.ID]{return empty,ErrPolicyReplay}
  if _,ok:=outcomeUtility(o.Class);!ok{return empty,ErrPolicyReplay}
  ids[o.ID]=true
  if o.Epoch<=f.TrainingThrough{hasTrain=true}else{hasHeld=true}
 }
 if !hasTrain||!hasHeld{return empty,ErrPolicyReplay}
 // Each historical epoch simulates one independent ranking choice from candidates
 // in that same epoch. Historical outcomes score only the selected choice.
 rank:=func(name string,o Observation)int64{
  if name=="diverse-efficiency" {return 1000000/int64(o.Compute)}
  return int64(len(o.Family))*1000
 }
 eval:=func(name string,held bool)int64{
  epochs:=map[uint64][]Observation{}
  for _,o:=range f.Candidates {
   if (o.Epoch>f.TrainingThrough)!=held{continue}
   epochs[o.Epoch]=append(epochs[o.Epoch],o)
  }
  keys:=make([]uint64,0,len(epochs));for e:=range epochs{keys=append(keys,e)}
  sort.Slice(keys,func(i,j int)bool{return keys[i]<keys[j]})
  var utility int64
  for _,e:=range keys {
   xs:=epochs[e]
   sort.Slice(xs,func(i,j int)bool{
    ai,aj:=rank(name,xs[i]),rank(name,xs[j])
    if ai!=aj{return ai>aj}
    return xs[i].ID<xs[j].ID
   })
   value,_:=outcomeUtility(xs[0].Class)
   utility+=value
  }
  return utility
 }
 a:=PolicyScore{Name:"baseline-family",TrainingUtility:eval("baseline-family",false),HoldoutUtility:eval("baseline-family",true)}
 b:=PolicyScore{Name:"diverse-efficiency",TrainingUtility:eval("diverse-efficiency",false),HoldoutUtility:eval("diverse-efficiency",true)}
 selected:=a.Name
 if b.TrainingUtility>a.TrainingUtility{selected=b.Name}
 return PolicyReplay{Schema:"forge.policy-replay.advisory.v1",FrozenSHA256:pin,SelectedPolicy:selected,Scores:[]PolicyScore{a,b}},nil
}
