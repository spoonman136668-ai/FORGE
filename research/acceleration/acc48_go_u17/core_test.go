package main
import("bytes";"testing")
func TestAllMethodsAreLossless(t *testing.T){for _,c:=range cohorts{a:=source(c,98101,2);if len(a)!=historySize{t.Fatal("size drift")};for _,m:=range modes{p,_,e:=serialize(m,a);if e!=nil{t.Fatal(e)};x,e:=restore(m,p);if e!=nil||!bytes.Equal(a,x){t.Fatalf("%s/%s lossy",c,m)}}}}
func TestMalformedRuleReferenceFails(t *testing.T){if _,e:=restore("GRAMMAR",[]byte{1,0,1});e==nil{t.Fatal("accepted missing rule")}}
func TestIndependentSourceSeeds(t *testing.T){if bytes.Equal(source("REPEATED",98101,0),source("REPEATED",98103,0)){t.Fatal("seed reuse")}}
func TestActualWorkerResources(t *testing.T){a,e:=single("GRAMMAR","REPEATED",98101);if e!=nil{t.Fatal(e)};b,e:=single("RAW","REPEATED",98101);if e!=nil{t.Fatal(e)};if a.SourceSHA256!=b.SourceSHA256||a.SourceSHA256!=a.OutputSHA256||a.PeakRSSBytes==0{t.Fatal("source/resources invalid")}}
