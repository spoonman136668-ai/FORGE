//go:build windows

package main

import (
	"fmt"
	"syscall"
	"unsafe"
)
type processMemoryCounters struct {
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
func peakResidentBytes()(uint64,error){
	psapi:=syscall.NewLazyDLL("psapi.dll")
	get:=psapi.NewProc("GetProcessMemoryInfo")
	handle,_,e:=syscall.NewLazyDLL("kernel32.dll").NewProc("GetCurrentProcess").Call()
	if handle==0{return 0,fmt.Errorf("GetCurrentProcess: %v",e)}
	mem:=processMemoryCounters{Size:uint32(unsafe.Sizeof(processMemoryCounters{}))}
	ok,_,err:=get.Call(handle,uintptr(unsafe.Pointer(&mem)),uintptr(mem.Size))
	if ok==0{return 0,fmt.Errorf("GetProcessMemoryInfo: %v",err)}
	if mem.PeakWorkingSetSize==0{return 0,fmt.Errorf("zero peak working set")}
	return uint64(mem.PeakWorkingSetSize),nil
}
