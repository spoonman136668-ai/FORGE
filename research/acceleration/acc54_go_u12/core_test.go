package main
import("testing")
func TestIndexInRange(t *testing.T){for _,w:=range worlds{for i:=0;i<50000;i++{x:=indexAt(104101,i,w);if x<0||x>=pages*512{t.Fatalf("%s %d",w,x)}}}}
func TestPageCacheExact(t *testing.T){for _,mode:=range modes{r,e:=work(mode,"HOTSET",104101);if e!=nil{t.Fatal(e)};if r.PeakRSSBytes==0||r.Requests!=requests{t.Fatal("invalid real worker")}}}
