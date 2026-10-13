package watchdog

import "testing"
func TestIncidentIdentityStableAcrossPollingAndLaneOrder(t *testing.T){
 a,b:=obs("Wingless"),obs("Yggdrasil")
 first,err:=DiagnoseBoth(1301,[]Observation{b,a})
 if err!=nil||len(first)!=2{t.Fatal(first,err)}
 second,err:=DiagnoseBoth(2000,[]Observation{a,b})
 if err!=nil||len(second)!=2{t.Fatal(second,err)}
 for i:=range first {
  if IncidentKey(first[i])!=IncidentKey(second[i]){t.Fatal("duplicate incident due to polling")}
 }
 a.JournalHeadSHA256="bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
 next,err:=DiagnoseBoth(2000,[]Observation{a,b})
 if err!=nil||IncidentKey(next[0])==IncidentKey(first[0]){t.Fatal("changed head not detected",err)}
}
func TestNoIncidentForHealthyOrUntrustedState(t *testing.T){
 a,b:=obs("Wingless"),obs("Yggdrasil")
 incidents,err:=DiagnoseBoth(1200,[]Observation{a,b})
 if err!=nil||len(incidents)!=0{t.Fatal(incidents,err)}
 a.Authenticated=false
 if _,err:=DiagnoseBoth(1500,[]Observation{a,b});err==nil{t.Fatal("untrusted observation")}
}
