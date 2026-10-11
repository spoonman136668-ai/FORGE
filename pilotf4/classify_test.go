package pilotf4
import ("encoding/json";"testing";"strings")
func TestF4NoSyntheticReceiptEscalation(t *testing.T){
 f:=Frozen{}
 f.Wingless.Train=[]int{10103,10111,10141,10151}
 f.Wingless.Hold=[]int{10211,10223,10243,10253}
 r:=Raw{Schema:RawSchema,Generation:"F4",Lane:"Wingless",
  SourceSHA:strings.Repeat("a",40),RunID:"17",FreezeBlob:FreezeBlob,SyntheticOnly:true}
 for i:=0;i<4;i++{r.Rows=append(r.Rows,Row{
  TrainSeed:f.Wingless.Train[i],HeldoutSeed:f.Wingless.Hold[i],
  Cases:240,Bounded:true,Correct:240,Baseline:0,Control:0})}
 raw,_:=json.Marshal(r)
 d,e:=ClassifyOriginal(raw,"Wingless",f)
 if e!=nil||d.Status!="SUPPORTED"||d.ScientificAccepted{t.Fatalf("%+v %v",d,e)}
 r.Rows[0].Bounded=false
 bad,_:=json.Marshal(r)
 if _,err:=ClassifyOriginal(bad,"Wingless",f);err==nil{t.Fatal("accepted invalid capacity")}
 r.Rows[0].Bounded=true
 r.Rows[0].Correct=0
 mixed,_:=json.Marshal(r)
 d,e=ClassifyOriginal(mixed,"Wingless",f)
 if e!=nil||d.Status!="MIXED"{t.Fatalf("negative partial improperly upgraded or downgraded: %+v %v",d,e)}
 r.Rows[0].Correct=240;r.SourceSHA="bad"
 bad,_=json.Marshal(r)
 if _,err:=ClassifyOriginal(bad,"Wingless",f);err==nil{t.Fatal("accepted bad provenance")}
}
