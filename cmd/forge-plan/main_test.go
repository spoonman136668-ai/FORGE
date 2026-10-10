package main

import (
 "bytes"
 "encoding/json"
 "os"
 "path/filepath"
 "strings"
 "testing"

 "github.com/spoonman136668-ai/forge/contracts"
 "github.com/spoonman136668-ai/forge/planner"
)
func fixture(t *testing.T)(string,string){
 t.Helper()
 f:=planner.FrozenPortfolio{Schema:planner.InputSchema,AuthorityEpoch:9,ConsumedSeedIdentities:[]string{},
  Observations:[]contracts.Observation{
   {Schema:contracts.ObservationSchema,Lane:contracts.Wingless,AuthorityEpoch:9,SourceWitnessSHA256:strings.Repeat("a",64),LedgerWitnessSHA256:strings.Repeat("b",64),LatestOutcome:"UNKNOWN"},
   {Schema:contracts.ObservationSchema,Lane:contracts.Yggdrasil,AuthorityEpoch:9,SourceWitnessSHA256:strings.Repeat("a",64),LedgerWitnessSHA256:strings.Repeat("b",64),LatestOutcome:"NEGATIVE"},
  },Candidates:[]planner.Candidate{}}
 pin,err:=planner.FreezeSHA256(f);if err!=nil{t.Fatal(err)}
 raw,err:=json.Marshal(f);if err!=nil{t.Fatal(err)}
 path:=filepath.Join(t.TempDir(),"frozen.json")
 if err:=os.WriteFile(path,raw,0600);err!=nil{t.Fatal(err)}
 return path,pin
}
func TestCLIReadOnlyDeterministicNoCandidatesInvented(t *testing.T){
 path,pin:=fixture(t);var out bytes.Buffer
 if err:=run([]string{"-frozen",path,"-pin",pin},&out);err!=nil{t.Fatal(err)}
 var d planner.Decision
 if err:=json.Unmarshal(out.Bytes(),&d);err!=nil{t.Fatal(err)}
 if len(d.Lanes)!=2||d.Lanes[0].Draft!=nil||d.Lanes[1].Draft!=nil||d.DispatchAuthorized||d.ScientificAdmitted||d.AcceptedRefMutation{t.Fatalf("unauthorized planning: %+v",d)}
}
func TestCLIFrozenIdentityAndCanonicalJSONAreMandatory(t *testing.T){
 path,pin:=fixture(t)
 old,err:=os.ReadFile(path);if err!=nil{t.Fatal(err)}
 cases:=[]struct{name string;data []byte;hash string}{
  {"wrong_pin",old,strings.Repeat("0",64)},
  {"unknown_key",bytes.Replace(old,[]byte(`"schema":`),[]byte(`"extra":true,"schema":`),1),pin},
  {"duplicate",bytes.Replace(old,[]byte(`"schema":`),[]byte(`"schema":"not-canonical","schema":`),1),pin},
  {"whitespace",bytes.Replace(old,[]byte(`,"authority_epoch":`),[]byte(`, "authority_epoch":`),1),pin},
  {"trailing",append(append([]byte{},old...),[]byte("true")...),pin},
 }
 for _,tc:=range cases{t.Run(tc.name,func(t *testing.T){
  if err:=os.WriteFile(path,tc.data,0600);err!=nil{t.Fatal(err)}
  var out bytes.Buffer
  if err:=run([]string{"-frozen",path,"-pin",tc.hash},&out);err==nil||out.Len()!=0{t.Fatalf("malformed portfolio accepted: %s",out.String())}
 })}
}
