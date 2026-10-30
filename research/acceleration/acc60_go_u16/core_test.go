package main
import "testing"
func TestCompiledWeights(t *testing.T){for _,s:=range []uint64{116101,116103,116107,116109,116111}{for _,i:=range []int{0,1,15,63,127,255}{for _,j:=range []int{0,2,14,64,128,255}{if compiledWeight(s,i,j)!=weight(s,i,j){t.Fatalf("mismatch %d %d %d",s,i,j)}}}}}
