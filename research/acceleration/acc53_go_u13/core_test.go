package main
import("testing")
func TestAbsentNoFabrication(t *testing.T){for _,arm:=range arms{m:=newModel(arm);m.Add(7,11);if x,ok:=m.Find(7);!ok||x!=11{t.Fatalf("%s inserted key absent",arm)};if _,ok:=m.Find(12);ok{t.Fatalf("%s fabricated key",arm)}}}
func TestPublicDataPairing(t *testing.T){a,e:=work("SKETCH512","REPEAT",103101);if e!=nil{t.Fatal(e)};b,e:=work("EXACT","REPEAT",103101);if e!=nil{t.Fatal(e)};if a.SourceSHA256!=b.SourceSHA256||a.TruthSHA256!=b.TruthSHA256||a.FalsePositives>0{t.Fatal("source or false positive regression")}}
