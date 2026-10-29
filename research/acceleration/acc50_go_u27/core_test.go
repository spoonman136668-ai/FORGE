package main
import("testing")
func TestExactAgainstIndependentPostorder(t *testing.T){for _,c:=range cohorts{for i:=0;i<100;i++{n:=source(100101,0,i,c);v:=exactByPostorder(n);if eval(n)!=v||eval(fold(n))!=v||eval(rewrite(n,map[ck]*node{}))!=v{t.Fatal("typed rewrite changed integer semantics")}}}}
func TestPublicSourcePaired(t *testing.T){a,e:=work("DIRECT","REPEATED",100101);if e!=nil{t.Fatal(e)};b,e:=work("TYPED_REWRITE","REPEATED",100101);if e!=nil{t.Fatal(e)};if a.SourceSHA256!=b.SourceSHA256||a.TruthSHA256!=b.TruthSHA256||a.OutputSHA256!=b.OutputSHA256{t.Fatal("unmatched exact source")}}
