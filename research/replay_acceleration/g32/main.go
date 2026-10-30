package main
import("crypto/sha256";"encoding/hex";"encoding/json";"flag";"fmt";"os";"os/exec";"runtime";"sync";"time")
type R struct{Schema string `json:"schema"`; OS string `json:"os"`; Role string `json:"role"`; Children int `json:"children"`; TotalDescendantCPU float64 `json:"total_descendant_cpu_s"`; MaxIndividualPeakRSS uint64 `json:"max_individual_peak_rss_bytes"`; SumIndividualPeakRSS uint64 `json:"sum_individual_peak_rss_bytes_upper_bound_not_concurrent_peak"`; ElapsedMS int64 `json:"elapsed_ms"`; Digest string `json:"digest"`; Scope string `json:"scope"`}
func runChild(exe,role string)(R,float64,error){cmd:=exec.Command(exe,"-role="+role);b,e:=cmd.Output();if e!=nil{return R{},0,e};var r R;if e=json.Unmarshal(b,&r);e!=nil{return R{},0,e};if cmd.ProcessState==nil{return R{},0,fmt.Errorf("no processstate")};cpu:=(cmd.ProcessState.UserTime()+cmd.ProcessState.SystemTime()).Seconds();return r,cpu,nil}
func main(){role:=flag.String("role","parent","");flag.Parse();exe,e:=os.Executable();if e!=nil{panic(e)}
 if *role=="worker" {start:=time.Now();var x uint64=27182818;for time.Since(start)<650*time.Millisecond{x=(x*1664525+1013904223)^uint64(time.Now().UnixNano()&7)};h:=sha256.Sum256([]byte(fmt.Sprint(x)));m,e:=peakRSS();if e!=nil{panic(e)};json.NewEncoder(os.Stdout).Encode(R{Schema:"forge.rar.g32.cooperative-tree.v1",OS:runtime.GOOS,Role:*role,Children:0,MaxIndividualPeakRSS:m,SumIndividualPeakRSS:m,ElapsedMS:time.Since(start).Milliseconds(),Digest:hex.EncodeToString(h[:]),Scope:"SELF_ONLY"});return}
 if *role!="parent"&&*role!="middle"{panic("invalid role")};start:=time.Now()
 var wg sync.WaitGroup;type result struct{r R;cpu float64;err error};rows:=make([]result,2)
 for i:=0;i<2;i++ {wg.Add(1);go func(i int){defer wg.Done();child:="worker";if *role=="parent"{child="middle"};r,c,e:=runChild(exe,child);rows[i]=result{r,c,e}}(i)}
 wg.Wait();r:=R{Schema:"forge.rar.g32.cooperative-tree.v1",OS:runtime.GOOS,Role:*role,Children:2,Scope:"COOPERATIVE_SPAWNED_TREE_SUM_CPU_AND_SUM_OF_INDIVIDUAL_PEAK_RSS_UPPER_BOUND_NOT_CONCURRENT_TREE_PEAK"};s:=""
 for _,v:=range rows{if v.err!=nil{panic(v.err)};if v.r.OS!=runtime.GOOS||v.r.MaxIndividualPeakRSS==0{panic("invalid child receipt")};r.TotalDescendantCPU+=v.cpu+v.r.TotalDescendantCPU;r.SumIndividualPeakRSS+=v.r.SumIndividualPeakRSS;if v.r.MaxIndividualPeakRSS>r.MaxIndividualPeakRSS{r.MaxIndividualPeakRSS=v.r.MaxIndividualPeakRSS};s+=v.r.Digest}
 h:=sha256.Sum256([]byte(s));r.Digest=hex.EncodeToString(h[:]);r.ElapsedMS=time.Since(start).Milliseconds();json.NewEncoder(os.Stdout).Encode(r)
}
