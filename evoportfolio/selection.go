// Package evoportfolio provides a bounded FORGE-native, nonexecuting
// family-diverse historical candidate portfolio. Its behavior is inspired by
// CKB-plane R4-R7 but it does not import that controller or scientific authority.
package evoportfolio

import (
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "sort"
)
var ErrFrozen=errors.New("FORGE_EVOPORTFOLIO_FROZEN_INVARIANT_VIOLATION")
const Schema="forge.evoportfolio.frozen.v1"

type Candidate struct {
 ID string `json:"id"`
 Family string `json:"family"`
 Signature string `json:"signature,omitempty"`
 SourceSHA string `json:"source_sha"`
 ScreenSHA string `json:"screen_sha"`
 HistoricalClass string `json:"historical_class"`
 Score int64 `json:"score"`
 ScreenCompute int64 `json:"screen_compute"`
 SealedCompute int64 `json:"sealed_compute"`
}
type Frozen struct {
 Schema string `json:"schema"`
 Lane string `json:"lane"`
 Epoch uint64 `json:"epoch"`
 HistoricalSourceSHA string `json:"historical_source_sha"`
 MaxScreenCompute int64 `json:"max_screen_compute"`
 MaxSealedCompute int64 `json:"max_sealed_compute"`
 MaxFinalists int `json:"max_finalists"`
 MaxPerFamily int `json:"max_per_family"`
 MaxScreensPerFamily int `json:"max_screens_per_family"`
 Candidates []Candidate `json:"candidates"`
}
type Decision struct {
 Schema string `json:"schema"`
 FrozenSHA256 string `json:"frozen_sha256"`
 Lane string `json:"lane"`
 Archive []Candidate `json:"archive"`
 Finalists []Candidate `json:"finalists"`
 ScreenComputeSpent int64 `json:"screen_compute_spent"`
 SealedComputeReserved int64 `json:"sealed_compute_reserved"`
 NegativeCount int `json:"negative_count"`
 MixedCount int `json:"mixed_count"`
 ScientificAccepted bool `json:"scientific_accepted"`
 DispatchAuthorized bool `json:"dispatch_authorized"`
 AcceptedRefMutation bool `json:"accepted_ref_mutation"`
}
func isHex(s string,n int)bool{
 if len(s)!=n{return false}
 for _,c:=range s{if !(c>='0'&&c<='9'||c>='a'&&c<='f'){return false}}
 return true
}
func validID(s string)bool{
 if len(s)<1||len(s)>72{return false}
 for _,c:=range s{
  if !(c>='a'&&c<='z'||c>='A'&&c<='Z'||c>='0'&&c<='9'||c=='-'||c=='_'){return false}
 }
 return true
}
func Digest(f Frozen)string{
 b,_:=json.Marshal(f)
 h:=sha256.Sum256(b)
 return hex.EncodeToString(h[:])
}
func Select(f Frozen,independentPin string)(Decision,error){
 var empty Decision
 if f.Schema!=Schema||(f.Lane!="Wingless"&&f.Lane!="Yggdrasil")||
  f.Epoch==0||!isHex(f.HistoricalSourceSHA,64)||
  f.MaxScreenCompute<1||f.MaxSealedCompute<1||
  f.MaxFinalists<1||f.MaxFinalists>5||
  f.MaxPerFamily<1||f.MaxPerFamily>5||
  f.MaxScreensPerFamily<1||f.MaxScreensPerFamily>32||
  len(f.Candidates)==0||len(f.Candidates)>160||
  !isHex(independentPin,64)||Digest(f)!=independentPin{return empty,ErrFrozen}
 byFamily:=map[string][]Candidate{}
 ids:=map[string]bool{}
 sources:=map[string]bool{}
 screens:=map[string]bool{}
 archive:=append([]Candidate(nil),f.Candidates...)
 var spent int64
 neg,mixed:=0,0
 for _,c:=range f.Candidates{
  if !validID(c.ID)||!validID(c.Family)||(c.Signature!=""&&!validID(c.Signature))||!isHex(c.SourceSHA,40)||
   !isHex(c.ScreenSHA,64)||ids[c.ID]||sources[c.SourceSHA]||screens[c.ScreenSHA]||
   c.ScreenCompute<1||c.SealedCompute<1||c.ScreenCompute>f.MaxScreenCompute||
   c.SealedCompute>f.MaxSealedCompute||c.Score< -1000000||c.Score>1000000{
   return empty,ErrFrozen
  }
  if c.HistoricalClass!="SUPPORTED"&&c.HistoricalClass!="MIXED"&&
   c.HistoricalClass!="NEGATIVE"&&c.HistoricalClass!="INVALID"&&
   c.HistoricalClass!="CONSUMED_INDETERMINATE"{return empty,ErrFrozen}
  ids[c.ID]=true;sources[c.SourceSHA]=true;screens[c.ScreenSHA]=true
  if spent>f.MaxScreenCompute-c.ScreenCompute{return empty,ErrFrozen}
  spent+=c.ScreenCompute
  byFamily[c.Family]=append(byFamily[c.Family],c)
  if c.HistoricalClass=="NEGATIVE"{neg++}
  if c.HistoricalClass=="MIXED"{mixed++}
 }
 families:=make([]string,0,len(byFamily))
 for family,items:=range byFamily{
  if len(items)>f.MaxScreensPerFamily||len(byFamily)>5{return empty,ErrFrozen}
  families=append(families,family)
  sort.Slice(items,func(i,j int)bool{
   if items[i].Score!=items[j].Score{return items[i].Score>items[j].Score}
   if items[i].SealedCompute!=items[j].SealedCompute{return items[i].SealedCompute<items[j].SealedCompute}
   return items[i].ID<items[j].ID
  })
  byFamily[family]=items
 }
 sort.Strings(families)
 sort.Slice(archive,func(i,j int)bool{return archive[i].ID<archive[j].ID})
 finalists:=[]Candidate{}
 seen:=map[string]bool{}
 usedSignatures:=map[string]bool{}
 var reserved int64
 for round:=0;round<f.MaxPerFamily&&len(finalists)<f.MaxFinalists;round++{
  for _,family:=range families{
   if len(finalists)>=f.MaxFinalists{break}
   taken:=0
   for _,x:=range finalists{if x.Family==family{taken++}}
   if taken>=f.MaxPerFamily{continue}
   for _,c:=range byFamily[family]{
    if seen[c.ID]||c.HistoricalClass=="INVALID"||
     c.HistoricalClass=="CONSUMED_INDETERMINATE"{continue}
    if reserved>f.MaxSealedCompute-c.SealedCompute{continue}
    signature:=c.Signature
    if signature==""{signature="legacy:"+c.ID}
    if usedSignatures[signature]{continue}
    finalists=append(finalists,c);seen[c.ID]=true;usedSignatures[signature]=true
    reserved+=c.SealedCompute
    break
   }
  }
 }
 return Decision{
  Schema:"forge.evoportfolio.advisory.v1",
  FrozenSHA256:independentPin,Lane:f.Lane,
  Archive:archive,Finalists:finalists,
  ScreenComputeSpent:spent,SealedComputeReserved:reserved,
  NegativeCount:neg,MixedCount:mixed,
 },nil
}
