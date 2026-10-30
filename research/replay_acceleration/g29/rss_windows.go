//go:build windows
package main
import("fmt";"syscall";"unsafe")
type pmc struct{Size,Faults uint32; PeakWorkingSet,WorkingSet,PeakPaged,Paged,PeakNonPaged,NonPaged,Pagefile,PeakPagefile uintptr}
func peakRSS()(uint64,error){
 kernel:=syscall.NewLazyDLL("kernel32.dll")
 h,_,e:=kernel.NewProc("GetCurrentProcess").Call();if h==0{return 0,fmt.Errorf("process: %v",e)}
 var p pmc;p.Size=uint32(unsafe.Sizeof(p))
 ok,_,e:=syscall.NewLazyDLL("psapi.dll").NewProc("GetProcessMemoryInfo").Call(h,uintptr(unsafe.Pointer(&p)),uintptr(p.Size))
 if ok==0||p.PeakWorkingSet==0{return 0,fmt.Errorf("peak rss: %v",e)}
 return uint64(p.PeakWorkingSet),nil
}
