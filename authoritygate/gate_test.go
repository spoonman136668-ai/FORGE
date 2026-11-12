package authoritygate

import (
 "errors"
 "testing"
)
const a="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
const b="bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
func ok(id uint64,tree string) Attestation {
 return Attestation{RunID:id,TreeSHA:tree,Qualified:true,ImmutableEvidence:true,NativeWindows:true,FrozenControlsUnchanged:true}
}
func TestExactTreePreflight(t *testing.T) {
 for _,tt:=range []struct{
  name string
  in Request
  allowed bool
  want error
  run uint64
 }{
  {"exact accepted",Request{TreeSHA:a,Qualifications:[]Attestation{ok(3,b),ok(2,a)}},true,nil,2},
  {"historical other tree",Request{TreeSHA:a,Qualifications:[]Attestation{ok(2,b)}},false,ErrUnqualified,0},
  {"no attestation",Request{TreeSHA:a},false,ErrUnqualified,0},
  {"duplicate matched successes",Request{TreeSHA:a,Qualifications:[]Attestation{ok(1,a),ok(2,a)}},false,ErrAmbiguous,0},
  {"consumed",Request{TreeSHA:a,FirstUseConsumed:true,Qualifications:[]Attestation{ok(2,a)}},false,ErrConsumed,0},
  {"invalid target",Request{TreeSHA:"a",Qualifications:[]Attestation{ok(2,a)}},false,ErrInvalid,0},
  {"duplicate run",Request{TreeSHA:a,Qualifications:[]Attestation{ok(2,a),ok(2,b)}},false,ErrInvalid,0},
  {"missing immutable custody",Request{TreeSHA:a,Qualifications:[]Attestation{{RunID:2,TreeSHA:a,Qualified:true,NativeWindows:true,FrozenControlsUnchanged:true}}},false,ErrUnqualified,0},
  {"wrong OS",Request{TreeSHA:a,Qualifications:[]Attestation{{RunID:2,TreeSHA:a,Qualified:true,ImmutableEvidence:true,FrozenControlsUnchanged:true}}},false,ErrUnqualified,0},
  {"frozen controls drift",Request{TreeSHA:a,Qualifications:[]Attestation{{RunID:2,TreeSHA:a,Qualified:true,ImmutableEvidence:true,NativeWindows:true}}},false,ErrUnqualified,0},
  {"unqualified",Request{TreeSHA:a,Qualifications:[]Attestation{{RunID:2,TreeSHA:a,ImmutableEvidence:true,NativeWindows:true,FrozenControlsUnchanged:true}}},false,ErrUnqualified,0},
 }{
  t.Run(tt.name,func(t *testing.T){
   got,err:=Assess(tt.in)
   if got.Eligible!=tt.allowed || got.QualifierRunID!=tt.run || !errors.Is(err,tt.want) {
    t.Fatalf("decision=%+v error=%v; wanted eligible=%v run=%d err=%v",got,err,tt.allowed,tt.run,tt.want)
   }
  })
 }
}
func TestAssessDoesNotMutateInput(t *testing.T) {
 att:=[]Attestation{ok(8,a)}
 in:=Request{TreeSHA:a,Qualifications:att}
 _,_ = Assess(in)
 if len(att)!=1 || att[0]!=ok(8,a) {t.Fatal("input attestation mutated")}
}
