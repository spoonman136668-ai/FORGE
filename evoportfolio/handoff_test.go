package evoportfolio

import(
 "reflect"
 "strings"
 "testing"
)
func TestHandoffAccountsForEveryNegativeAndInvalid(t *testing.T){
 f:=fixture()
 f.MaxScreenCompute=12
 f.Candidates=append(f.Candidates,Candidate{ID:"uncertain",Family:"c",
  SourceSHA:strings.Repeat("1",40),ScreenSHA:strings.Repeat("1",64),
  HistoricalClass:"CONSUMED_INDETERMINATE",Score:999,ScreenCompute:2,SealedCompute:1},
  Candidate{ID:"negative",Family:"c",
  SourceSHA:strings.Repeat("2",40),ScreenSHA:strings.Repeat("2",64),
  HistoricalClass:"NEGATIVE",Score:-9,ScreenCompute:2,SealedCompute:1})
 h,err:=BuildHandoff(f,Digest(f));if err!=nil{t.Fatal(err)}
 if len(h.OrderedFinalistIDs)+len(h.OrderedNonfinalistIDs)!=6||
  h.InvalidCount!=1||h.IndeterminateCount!=1||
  h.DispatchAuthorized||h.ScientificAccepted{t.Fatalf("lost archive or invented authority: %+v",h)}
 for _,id:=range h.OrderedFinalistIDs{
  if id=="invalid"||id=="uncertain"{t.Fatal("inadmissible candidate selected")}
 }
 reversed:=fixture()
 reversed.MaxScreenCompute=12
 reversed.Candidates=append(reversed.Candidates,f.Candidates[4:]...)
 reversed.Candidates[0],reversed.Candidates[3]=reversed.Candidates[3],reversed.Candidates[0]
 a,err:=BuildHandoff(reversed,Digest(reversed));if err!=nil{t.Fatal(err)}
 if !reflect.DeepEqual(h.OrderedFinalistIDs,a.OrderedFinalistIDs)||
  !reflect.DeepEqual(h.OrderedNonfinalistIDs,a.OrderedNonfinalistIDs){
  t.Fatal("portfolio result depends on historical listing order")
 }
}
func TestHandoffRejectsIdentityDrift(t *testing.T){
 f:=fixture()
 if _,err:=BuildHandoff(f,strings.Repeat("0",64));err==nil{t.Fatal("identity drift")}
 f.Candidates[1].SourceSHA=f.Candidates[0].SourceSHA
 if _,err:=BuildHandoff(f,Digest(f));err==nil{t.Fatal("duplicate source admitted")}
}
