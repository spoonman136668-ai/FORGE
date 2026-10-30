package main
import("testing")
func TestBoundedGrammar(t *testing.T){p:=grammar();if len(p)!=169{t.Fatalf("candidate universe %d",len(p))};for _,m:=range arms{v:=order(p,m);if len(v)!=len(p){t.Fatal("ordering")} ;found:=map[int]bool{};for _,i:=range v{if found[i]{t.Fatal("duplicate")};found[i]=true}}}
func TestTrainHeldoutDisjoint(t *testing.T){for j:=0;j<32;j++{if xAt(106101,0,j,true)<100{t.Fatal("heldout leak")}}}
