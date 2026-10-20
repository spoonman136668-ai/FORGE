//go:build windows

package lcrm01

import ("errors";"syscall";"unsafe")

type o2WindowsCounters struct{
    Size uint32
    PageFaultCount uint32
    PeakWorkingSetSize uintptr
    WorkingSetSize uintptr
    QuotaPeakPagedPoolUsage uintptr
    QuotaPagedPoolUsage uintptr
    QuotaPeakNonPagedPoolUsage uintptr
    QuotaNonPagedPoolUsage uintptr
    PagefileUsage uintptr
    PeakPagefileUsage uintptr
}
func o2FiletimeTicks(x syscall.Filetime)uint64{
    return uint64(x.HighDateTime)<<32|uint64(x.LowDateTime)
}
func O2ProcessMetrics()(int64,int64,error){
    k:=syscall.NewLazyDLL("kernel32.dll")
    p:=syscall.NewLazyDLL("psapi.dll")
    get:=k.NewProc("GetCurrentProcess")
    times:=k.NewProc("GetProcessTimes")
    memory:=p.NewProc("GetProcessMemoryInfo")
    process,_,_:=get.Call()
    var created,exited,kernel,user syscall.Filetime
    status,_,err:=times.Call(process,uintptr(unsafe.Pointer(&created)),
        uintptr(unsafe.Pointer(&exited)),uintptr(unsafe.Pointer(&kernel)),
        uintptr(unsafe.Pointer(&user)))
    if status==0{return 0,0,errors.Join(errors.New("O2_WINDOWS_PROCESS_CPU"),err)}
    m:=o2WindowsCounters{Size:uint32(unsafe.Sizeof(o2WindowsCounters{}))}
    status,_,err=memory.Call(process,uintptr(unsafe.Pointer(&m)),uintptr(m.Size))
    if status==0{return 0,0,errors.Join(errors.New("O2_WINDOWS_PEAK_RSS"),err)}
    return int64((o2FiletimeTicks(kernel)+o2FiletimeTicks(user))*100),
       int64(m.PeakWorkingSetSize),nil
}
