package eligibility

import (
 "errors"
 "strings"
 "testing"
)
func TestLedgerConflictDetector(t *testing.T){
 p,_:=fixture()
 fp,err:=Fingerprint(p);if err!=nil{t.Fatal(err)}
 base:=LedgerSnapshot{Schema:"forge.eligibility.ledger-snapshot.v1",Lane:"Wingless",Generation:1,ConsumedCohorts:[]string{},Starts:[]StartRecord{}}
 check:=func(s LedgerSnapshot,complete bool,pin string)error{
  if pin=="auto"{var e error;pin,e=LedgerFingerprint(s);if e!=nil{t.Fatal(e)}}
  return VerifyLedger(p,s,pin,complete)
 }
 if err:=check(base,true,"auto");err!=nil{t.Fatal(err)}
 cases:=[]struct{name string;mutate func(*LedgerSnapshot);complete bool;pin string}{
  {"missing independent authentication",func(*LedgerSnapshot){},false,"auto"},
  {"wrong pin",func(*LedgerSnapshot){},true,strings.Repeat("0",64)},
  {"used cohort",func(s *LedgerSnapshot){s.ConsumedCohorts=[]string{p.CohortSHA256}},true,"auto"},
  {"duplicate cohort",func(s *LedgerSnapshot){s.ConsumedCohorts=[]string{p.CohortSHA256,p.CohortSHA256}},true,"auto"},
  {"prior start",func(s *LedgerSnapshot){s.Starts=[]StartRecord{{fp,"STARTED"}}},true,"auto"},
  {"terminal start",func(s *LedgerSnapshot){s.Starts=[]StartRecord{{fp,"TERMINAL"}}},true,"auto"},
  {"uncertain start",func(s *LedgerSnapshot){s.Starts=[]StartRecord{{fp,"INDETERMINATE"}}},true,"auto"},
  {"duplicate start",func(s *LedgerSnapshot){s.Starts=[]StartRecord{{fp,"STARTED"},{fp,"TERMINAL"}}},true,"auto"},
  {"invalid state",func(s *LedgerSnapshot){s.Starts=[]StartRecord{{strings.Repeat("c",64),"READY"}}},true,"auto"},
  {"lane collision",func(s *LedgerSnapshot){s.Lane="Yggdrasil"},true,"auto"},
  {"empty generation",func(s *LedgerSnapshot){s.Generation=0},true,"auto"},
 }
 for _,tc:=range cases{t.Run(tc.name,func(t *testing.T){
  s:=base;tc.mutate(&s)
  if err:=check(s,tc.complete,tc.pin);!errors.Is(err,ErrBlocked){t.Fatalf("must block: %v",err)}
 })}
}
