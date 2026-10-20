// Source-free O2 process arm executable. Never touches original scientific
// sources or dispatches an experiment. Measurements include the full process.
package main

import ("encoding/json";"fmt";"os";
    "github.com/spoonman136668-ai/forge/research/lcrm01")
type Report struct {
    lcrm01.O2Report
    ProcessCPUTimeNs int64
    PeakRSSBytes int64
    FullProcessMetricAvailable bool
}
func main(){
    if len(os.Args)!=2{fmt.Fprintln(os.Stderr,"O2_ARM_REQUIRED");os.Exit(2)}
    r,err:=lcrm01.O2Screen(lcrm01.O2Arm(os.Args[1]))
    if err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(1)}
    cpu,rss,err:=lcrm01.O2ProcessMetrics()
    if err!=nil{fmt.Fprintln(os.Stderr,err);os.Exit(1)}
    out:=Report{O2Report:r,ProcessCPUTimeNs:cpu,
        PeakRSSBytes:rss,FullProcessMetricAvailable:true}
    if cpu<0||rss<=0||r.MaxPhysicalSlots!=8||r.Episodes!=6||
        r.ScientificAccepted||r.IndependentFirstUse||r.OptimizerAdmitted{
        fmt.Fprintln(os.Stderr,"O2_RESOURCE_OR_ADMISSION_INVARIANT_FAILED")
        os.Exit(1)
    }
    if err:=json.NewEncoder(os.Stdout).Encode(out);err!=nil{
        fmt.Fprintln(os.Stderr,err);os.Exit(1)
    }
}
