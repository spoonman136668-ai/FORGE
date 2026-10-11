package evoportfolio

import ("testing";"strings")
func TestProgressionOnlyMovesOverAuthenticatedOrder(t *testing.T){
 f:=fixture()
 h,err:=BuildHandoff(f,Digest(f));if err!=nil{t.Fatal(err)}
 first,err:=NextAdvisory(h,nil);if err!=nil||first.NextID!="alpha"||first.DispatchAuthorized{t.Fatalf("%+v %v",first,err)}
 second,err:=NextAdvisory(h,[]string{"alpha"});if err!=nil||second.NextID!="gamma"{t.Fatalf("%+v %v",second,err)}
 for _,bad:=range [][]string{{"gamma"},{"alpha","alpha"},{"invalid"},{"alpha","beta"}}{
  if _,err:=NextAdvisory(h,bad);err==nil{t.Fatal("unverified progression accepted",bad)}
 }
 all:=[]string{"alpha","gamma","beta"}
 last,err:=NextAdvisory(h,all)
 if err!=nil||!last.Exhausted||last.NextID!=""{t.Fatalf("%+v %v",last,err)}
 h.DecisionSHA256=strings.Repeat("x",64)
 if _,err:=NextAdvisory(h,nil);err==nil{t.Fatal("bad decision identity accepted")}
}
