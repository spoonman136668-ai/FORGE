package main
import "testing"
func TestDeterminism(t *testing.T){a,ay:=sequence(108101,"DELAY16",3,false);b,by:=sequence(108101,"DELAY16",3,false);if a!=b||ay!=by{t.Fatal("source drift")}}
func TestRidge(t *testing.T){x:=[][]float64{{1,0},{1,1},{1,2}};w:=fit(x,[]float64{0,1,2});if predict(w,[]float64{1,2})!=1{t.Fatal("ridge")}}
