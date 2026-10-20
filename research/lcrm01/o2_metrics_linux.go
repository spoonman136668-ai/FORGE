//go:build linux

package lcrm01

import "syscall"

// O2ProcessMetrics reads OS lifetime process CPU and high-water resident
// memory including training, retention, runtime allocations and validation.
func O2ProcessMetrics()(int64,int64,error){
    var r syscall.Rusage
    if err:=syscall.Getrusage(syscall.RUSAGE_SELF,&r);err!=nil{return 0,0,err}
    cpu:=(r.Utime.Sec+r.Stime.Sec)*1000000000+
         (r.Utime.Usec+r.Stime.Usec)*1000
    return cpu,r.Maxrss*1024,nil
}
