package pilotf4

import (
 "bytes"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "io"
)
const RawSchema="forge.f4.synthetic-original.v1"
type Row struct{
 TrainSeed int `json:"train_seed"`
 HeldoutSeed int `json:"heldout_seed"`
 Cases int `json:"cases"`
 Correct int `json:"correct"`
 Baseline int `json:"baseline"`
 Control int `json:"control"`
 Hot int `json:"hot"`
 Bounded bool `json:"bounded"`
}
type Raw struct{
 Schema string `json:"schema"`
 Generation string `json:"generation"`
 Lane string `json:"lane"`
 SourceSHA string `json:"source_sha"`
 RunID string `json:"run_id"`
 FreezeBlob string `json:"freeze_blob"`
 SyntheticOnly bool `json:"synthetic_only"`
 ScientificAccepted bool `json:"scientific_accepted"`
 Rows []Row `json:"rows"`
}
type Disposition struct{
 Lane string `json:"lane"`
 Status string `json:"status"`
 Clauses [4]bool `json:"clauses"`
 OriginalSHA256 string `json:"original_sha256"`
 ScientificAccepted bool `json:"scientific_accepted"`
}
// rejectDuplicateJSONKeys refuses ambiguous duplicate keys at every nesting
// level. Scientific original raw evidence cannot be interpreted last-wins.
func rejectDuplicateJSONKeys(raw []byte)bool{
 d:=json.NewDecoder(bytes.NewReader(raw))
 d.UseNumber()
 var walk func()error
 walk=func()error{
  token,err:=d.Token()
  if err!=nil{return err}
  opener,ok:=token.(json.Delim)
  if !ok{return nil}
  if opener!='{'&&opener!='['{return ErrInvalid}
  seen:=map[string]bool{}
  for d.More(){
   if opener=='{'{
    key,err:=d.Token()
    if err!=nil{return err}
    value,ok:=key.(string)
    if !ok||seen[value]{return ErrInvalid}
    seen[value]=true
   }
   if err:=walk();err!=nil{return err}
  }
  closer,err:=d.Token()
  if err!=nil{return err}
  if opener=='{'&&closer!=json.Delim('}')||
   opener=='['&&closer!=json.Delim(']'){return ErrInvalid}
  return nil
 }
 if walk()!=nil{return true}
 _,err:=d.Token()
 return err!=io.EOF
}
func validSource(s string)bool{
 if len(s)!=40{return false}
 for _,c:=range s{if !(c>='0'&&c<='9'||c>='a'&&c<='f'){return false}}
 return true
}
func ClassifyOriginal(b []byte,lane string,f Frozen)(Disposition,error){
 var zero Disposition
 if len(b)==0||len(b)>65536||rejectDuplicateJSONKeys(b){return zero,ErrInvalid}
 d:=json.NewDecoder(bytes.NewReader(b));d.DisallowUnknownFields()
 var r Raw
 if d.Decode(&r)!=nil{return zero,ErrInvalid}
 var extra any
 if d.Decode(&extra)!=io.EOF{return zero,ErrInvalid}
 if r.Schema!=RawSchema||r.Generation!="F4"||r.Lane!=lane||
  r.FreezeBlob!=FreezeBlob||!r.SyntheticOnly||r.ScientificAccepted||
  !validSource(r.SourceSHA)||r.RunID==""{return zero,ErrInvalid}
 for _,c:=range r.RunID{if c<'0'||c>'9'{return zero,ErrInvalid}}
 var train,hold []int
 var cases,total,correct,baseline,control,hot int
 if lane=="Wingless"{train=f.Wingless.Train;hold=f.Wingless.Hold;total=960}
 if lane=="Yggdrasil"{train=f.Yggdrasil.Train;hold=f.Yggdrasil.Hold;total=160}
 if total==0||len(r.Rows)!=len(hold){return zero,ErrInvalid}
 for i,row:=range r.Rows{
  n:=240
  cap:=n
  if lane=="Yggdrasil"{n=20;cap=6}
  if row.TrainSeed!=train[i]||row.HeldoutSeed!=hold[i]||
   row.Cases!=n||!row.Bounded||row.Correct<0||row.Correct>cap||
   row.Baseline<0||row.Baseline>cap||row.Control<0||row.Control>n||
   row.Hot<0||row.Hot>12{return zero,ErrInvalid}
  cases+=row.Cases;correct+=row.Correct;baseline+=row.Baseline
  control+=row.Control;hot+=row.Hot
 }
 if cases!=total{return zero,ErrInvalid}
 var flags [4]bool
 if lane=="Wingless"{
  flags=[4]bool{float64(correct)/960>=.85,
   float64(correct-baseline)/960>=.25,
   float64(correct-control)/960>=.15,true}
 }else{
  flags=[4]bool{float64(correct)/48>=.30,
   float64(correct-baseline)/48>=.20,
   float64(hot)/96>=.55,true}
 }
 // Capacity is a mandatory validity gate, not positive efficacy evidence.
 // All three prespecified scientific comparisons failing is a NEGATIVE
 // finding, not MIXED merely because the fixed-capacity check passed.
 n:=0;for _,ok:=range flags[:3]{if ok{n++}}
 label:="MIXED"
 if n==3&&flags[3]{label="SUPPORTED"}
 if n==0{label="NEGATIVE"}
 h:=sha256.Sum256(b)
 return Disposition{Lane:lane,Status:label,Clauses:flags,
  OriginalSHA256:hex.EncodeToString(h[:])},nil
}
