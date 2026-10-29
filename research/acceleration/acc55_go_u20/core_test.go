package main
import("testing")
func TestProgramCandidateSelectionUniverse(t *testing.T){p:=grammar();if len(p)!=169{t.Fatalf("wrong program count %d",len(p))};for i:=1;i<len(p);i++{if p[i].Text<=p[i-1].Text{t.Fatal("ordering")}}}
func TestHeldoutSeparated(t *testing.T){for i:=0;i<32;i++{if xAt(105101,3,i,true)<100{t.Fatal("leak")}}}
