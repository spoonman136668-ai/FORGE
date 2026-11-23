package evoportfolio
import (
 "encoding/json"
 "reflect"
 "strings"
 "testing"
)
func fixture()Frozen{
 c:=[]Candidate{
  {ID:"alpha",Family:"a",SourceSHA:strings.Repeat("a",40),ScreenSHA:strings.Repeat("a",64),HistoricalClass:"SUPPORTED",Score:9,ScreenCompute:2,SealedCompute:3},
  {ID:"beta",Family:"a",SourceSHA:strings.Repeat("b",40),ScreenSHA:strings.Repeat("b",64),HistoricalClass:"NEGATIVE",Score:8,ScreenCompute:2,SealedCompute:3},
  {ID:"gamma",Family:"b",SourceSHA:strings.Repeat("c",40),ScreenSHA:strings.Repeat("c",64),HistoricalClass:"MIXED",Score:8,ScreenCompute:2,SealedCompute:2},
  {ID:"invalid",Family:"b",SourceSHA:strings.Repeat("d",40),ScreenSHA:strings.Repeat("d",64),HistoricalClass:"INVALID",Score:100,ScreenCompute:2,SealedCompute:2},
 }
 return Frozen{Schema:Schema,Lane:"Wingless",Epoch:1,
  HistoricalSourceSHA:strings.Repeat("e",64),
  MaxScreenCompute:8,MaxSealedCompute:8,
  MaxFinalists:3,MaxPerFamily:2,MaxScreensPerFamily:2,Candidates:c}
}
func TestR18FrozenPortfolioFamilyDiversityAndNegativeRetention(t *testing.T){
 f:=fixture();r,err:=Select(f,Digest(f));if err!=nil{t.Fatal(err)}
 if len(r.Archive)!=4||r.NegativeCount!=1||r.MixedCount!=1||
  len(r.Finalists)!=3||r.Finalists[0].ID!="alpha"||
  r.Finalists[1].ID!="gamma"||r.Finalists[2].ID!="beta"||
  r.SealedComputeReserved!=8||r.ScreenComputeSpent!=8||
  r.ScientificAccepted||r.DispatchAuthorized||r.AcceptedRefMutation{
  t.Fatalf("bad native portfolio: %+v",r)
 }
 reordered:=fixture()
 reordered.Candidates[0],reordered.Candidates[3]=reordered.Candidates[3],reordered.Candidates[0]
 other,err:=Select(reordered,Digest(reordered));if err!=nil{t.Fatal(err)}
 if !reflect.DeepEqual(r.Finalists,other.Finalists)||!reflect.DeepEqual(r.Archive,other.Archive){
  t.Fatal("candidate input order changes frozen portfolio selection")
 }
}
func TestR18IdentityBudgetAndSealedSafety(t *testing.T){
 cases:=[]struct{name string;change func(*Frozen)}{
  {"budget",func(f *Frozen){f.MaxScreenCompute=7}},
  {"bad-sha",func(f *Frozen){f.Candidates[0].SourceSHA="bad"}},
  {"duplicate",func(f *Frozen){f.Candidates[1].ScreenSHA=f.Candidates[0].ScreenSHA}},
  {"class",func(f *Frozen){f.Candidates[1].HistoricalClass="SEALED"}},
  {"per-family",func(f *Frozen){f.MaxScreensPerFamily=1}},
  {"lane",func(f *Frozen){f.Lane="CKB"}},
 }
 for _,tc:=range cases{
  t.Run(tc.name,func(t *testing.T){
   f:=fixture();tc.change(&f)
   if _,err:=Select(f,Digest(f));err==nil{t.Fatal("unsafe input admitted")}
  })
 }
 f:=fixture()
 if _,err:=Select(f,strings.Repeat("f",64));err==nil{t.Fatal("unpinned mutation admitted")}
 valid,err:=Select(f,Digest(f));if err!=nil{t.Fatal(err)}
 encoded,_:=json.Marshal(valid)
 if strings.Contains(string(encoded),"\"scientific_accepted\":true")||
  strings.Contains(string(encoded),"\"dispatch_authorized\":true"){t.Fatal("advisory escalated")}
}
