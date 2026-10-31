//go:build windows

package main

import (
	"errors"
	"syscall"
	"unsafe"
)

type winFiletime struct { Low uint32; High uint32 }
func (f winFiletime) nanos() int64 {
	return int64(uint64(f.High)<<32|uint64(f.Low))*100
}

type processMemoryCountersEx struct {
	CB uint32
	PageFaultCount uint32
	PeakWorkingSetSize uintptr
	WorkingSetSize uintptr
	QuotaPeakPagedPoolUsage uintptr
	QuotaPagedPoolUsage uintptr
	QuotaPeakNonPagedPoolUsage uintptr
	QuotaNonPagedPoolUsage uintptr
	PagefileUsage uintptr
	PeakPagefileUsage uintptr
	PrivateUsage uintptr
}

var (
	acc125Kernel32 = syscall.NewLazyDLL("kernel32.dll")
	acc125PSAPI = syscall.NewLazyDLL("psapi.dll")
	acc125GetCurrentProcess = acc125Kernel32.NewProc("GetCurrentProcess")
	acc125GetProcessTimes = acc125Kernel32.NewProc("GetProcessTimes")
	acc125GetProcessMemoryInfo = acc125PSAPI.NewProc("GetProcessMemoryInfo")
)

// PeakWorkingSetSize is a native Windows OS-reported process peak physical
// working-set counter. Process time uses kernel FILETIME, not Go heap stats.
func platformProcessUsage() (userNanos, systemNanos int64, peakRSSBytes uint64, err error) {
	handle, _, e := acc125GetCurrentProcess.Call()
	if handle == 0 { err = errors.New("ACC125_WIN_BAD_PROCESS_HANDLE"); return }
	var created, exited, kernel, user winFiletime
	rc, _, callErr := acc125GetProcessTimes.Call(
		handle,
		uintptr(unsafe.Pointer(&created)), uintptr(unsafe.Pointer(&exited)),
		uintptr(unsafe.Pointer(&kernel)), uintptr(unsafe.Pointer(&user)),
	)
	if rc == 0 {
		err = errors.Join(errors.New("ACC125_WIN_PROCESS_TIMES_FAILED"), callErr, e)
		return
	}
	memory := processMemoryCountersEx{CB: uint32(unsafe.Sizeof(processMemoryCountersEx{}))}
	rc, _, callErr = acc125GetProcessMemoryInfo.Call(handle,
		uintptr(unsafe.Pointer(&memory)), uintptr(memory.CB))
	if rc == 0 {
		err = errors.Join(errors.New("ACC125_WIN_PEAK_WORKING_SET_FAILED"), callErr)
		return
	}
	if memory.PeakWorkingSetSize == 0 {
		err = errors.New("ACC125_WIN_ZERO_PEAK_WORKING_SET")
		return
	}
	return user.nanos(), kernel.nanos(), uint64(memory.PeakWorkingSetSize), nil
}
