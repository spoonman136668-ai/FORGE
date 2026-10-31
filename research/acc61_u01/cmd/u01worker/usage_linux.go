//go:build linux

package main

import (
	"errors"
	"syscall"
)

// Linux ru_maxrss is the process maximum resident set size in KiB.
// User/system time come from the kernel, not Go heap or synthetic proxies.
func platformProcessUsage() (userNanos, systemNanos int64, peakRSSBytes uint64, err error) {
	var r syscall.Rusage
	if err = syscall.Getrusage(syscall.RUSAGE_SELF, &r); err != nil { return }
	if r.Maxrss <= 0 { err = errors.New("ACC125_LINUX_NO_PEAK_RSS"); return }
	userNanos = r.Utime.Sec*1e9+r.Utime.Usec*1e3
	systemNanos = r.Stime.Sec*1e9+r.Stime.Usec*1e3
	peakRSSBytes = uint64(r.Maxrss)*1024
	return
}
