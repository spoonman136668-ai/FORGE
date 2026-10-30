package main
import "testing"
func TestXOR(t *testing.T){a:=signature(109101,0,1,2);b:=signature(109101,0,3,4);if xor(xor(a,b),a)!=b{t.Fatal("XOR")}}
func TestOOD(t *testing.T){if qkey(109101,0,1,32,"OOD")<1000{t.Fatal("OOD query leak")}}
