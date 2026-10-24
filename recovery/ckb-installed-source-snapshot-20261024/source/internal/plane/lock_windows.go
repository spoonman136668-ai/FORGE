//go:build windows

package plane

import (
	"golang.org/x/sys/windows"
	"os"
)

func lockFile(f *os.File) error {
	return windows.LockFileEx(windows.Handle(f.Fd()), windows.LOCKFILE_EXCLUSIVE_LOCK|windows.LOCKFILE_FAIL_IMMEDIATELY, 0, 1, 0, &windows.Overlapped{})
}
func processAlive(pid int) bool {
	h, e := windows.OpenProcess(windows.SYNCHRONIZE, false, uint32(pid))
	if e != nil {
		return e != windows.ERROR_INVALID_PARAMETER
	}
	defer windows.CloseHandle(h)
	r, e := windows.WaitForSingleObject(h, 0)
	return e != nil || r != windows.WAIT_OBJECT_0
}
