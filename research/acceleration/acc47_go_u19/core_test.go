package main
import("testing")
func TestFiniteStateLearnsAndClamps(t *testing.T){m:=newModel("TSETLIN16");if m.Predict(0)!=0{t.Fatal("tie is not zero")};for i:=0;i<1000;i++{m.Fit(1,1)};if m.States[0]<=32768{t.Fatal("no reinforcement")};m.States[0]=65535;m.Fit(1,1);if m.States[0]!=65535{t.Fatal("overflow")}}
func TestSameSourceDifferentModels(t *testing.T){a,e:=work("TSETLIN16","SPARSE_OR",97101);if e!=nil{t.Fatal(e)};b,e:=work("LUT4","SPARSE_OR",97101);if e!=nil{t.Fatal(e)};if a.SourceSHA256!=b.SourceSHA256||a.FitSHA256!=b.FitSHA256||a.TruthSHA256!=b.TruthSHA256{t.Fatal("source mismatch")}}
func TestIndependentHeldout(t *testing.T){a:=features(97101,0,0,false);b:=features(97101,0,0,true);if a==b{t.Fatal("heldout reused training")};if target("DRIFT",0,0)!=target("SPARSE_OR",0,0){t.Fatal("early drift mismatch")}}
func TestStrongControlMemory(t *testing.T){if newModel("TSETLIN16").Bytes()>newModel("PERCEPTRON").Bytes(){t.Fatal("candidate too large")}}
