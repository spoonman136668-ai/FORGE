package main
import "testing"
func TestInvertibleBinding(t *testing.T){a:=signature(107101,0,3,5);b:=signature(107101,0,9,10);if bind(bind(a,b),a)!=b{t.Fatal("XOR mismatch")}}
func TestNoUnknownInControls(t *testing.T){if count("SHIFT")!=32||query(107101,0,1,32,"SHIFT")<1000{t.Fatal("source")}}
