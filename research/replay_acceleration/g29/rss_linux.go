//go:build linux
package main
import("fmt";"os";"strconv";"strings")
func peakRSS()(uint64,error){
 b,e:=os.ReadFile("/proc/self/status");if e!=nil{return 0,e}
 for _,l:=range strings.Split(string(b),"\n"){if strings.HasPrefix(l,"VmHWM:"){
  f:=strings.Fields(l);if len(f)!=3||f[2]!="kB"{return 0,fmt.Errorf("invalid VmHWM")}
  n,e:=strconv.ParseUint(f[1],10,64);return n*1024,e
 }}
 return 0,fmt.Errorf("no VmHWM")
}
