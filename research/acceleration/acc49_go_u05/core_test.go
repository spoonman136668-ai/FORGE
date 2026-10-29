package main
import("testing")
func TestSourcesIndependentAndStable(t *testing.T){a,b:=source("RECURRENT_STATE",99101,0,0);c,d:=source("RECURRENT_STATE",99101,0,64);if a!=c||b!=d{t.Fatal("recurrent source drift")};e,_:=source("NOVEL",99101,0,1);if e==a{t.Fatal("novel source reused")}}
func TestExactStateAndInputCacheKeys(t *testing.T){for _,m:=range modes{c:=newCache(m);a:=c.Apply(key{1,2});b:=c.Apply(key{3,2});if a!=transition(1,2)||b!=transition(3,2){t.Fatal("cache ignored state")}}}
func TestQualifiedRealWorker(t *testing.T){a,e:=single("U05_LOOKUP","RECURRENT_STATE",99101);if e!=nil{t.Fatal(e)};b,e:=single("DIRECT","RECURRENT_STATE",99101);if e!=nil{t.Fatal(e)};if a.SourceSHA256!=b.SourceSHA256||a.OutputSHA256!=b.OutputSHA256||a.PeakRSSBytes==0{t.Fatal("invalid exact source or RSS")}}
