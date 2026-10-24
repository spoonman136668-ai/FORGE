//go:build windows

package plane

import (
	"golang.org/x/sys/windows"
	"os/exec"
	"unsafe"
)

func configureHost(cmd *exec.Cmd) {}
func containHost() error {
	job, e := windows.CreateJobObject(nil, nil)
	if e != nil {
		return e
	}
	info := windows.JOBOBJECT_EXTENDED_LIMIT_INFORMATION{}
	info.BasicLimitInformation.LimitFlags = windows.JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
	if _, e = windows.SetInformationJobObject(job, windows.JobObjectExtendedLimitInformation, uintptr(unsafe.Pointer(&info)), uint32(unsafe.Sizeof(info))); e != nil {
		windows.CloseHandle(job)
		return e
	}
	if e = windows.AssignProcessToJobObject(job, windows.CurrentProcess()); e != nil {
		windows.CloseHandle(job)
		return e
	}
	// Intentionally held until process exit; never inherited by the child. Closing
	// it while the host runs would also terminate the host before its exit code.
	return nil
}
