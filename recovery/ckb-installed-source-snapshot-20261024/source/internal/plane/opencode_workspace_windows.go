//go:build windows

package plane

import "syscall"

const openCodeFileAttributeReparsePoint = 0x400

func openCodePathReparseUnsafe(path string) (bool, error) {
	p, err := syscall.UTF16PtrFromString(path)
	if err != nil {
		return false, err
	}
	attrs, err := syscall.GetFileAttributes(p)
	if err != nil {
		return false, err
	}
	return attrs&openCodeFileAttributeReparsePoint != 0, nil
}
