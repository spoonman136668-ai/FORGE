//go:build linux

package plane

import (
	"os"
	"syscall"
)

func lockFile(f *os.File) error { return syscall.Flock(int(f.Fd()), syscall.LOCK_EX|syscall.LOCK_NB) }
func processAlive(pid int) bool { e := syscall.Kill(pid, 0); return e == nil || e == syscall.EPERM }
