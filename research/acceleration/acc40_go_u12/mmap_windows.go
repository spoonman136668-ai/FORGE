//go:build windows

package main

import (
	"fmt"
	"os"
	"syscall"
	"unsafe"
)

type mappedRegion interface {
	ReadBlock(off int64)([]byte,error)
	Close()error
}
var kernel32Mapping=syscall.NewLazyDLL("kernel32.dll")
var createFileMapping=kernel32Mapping.NewProc("CreateFileMappingW")
var mapViewOfFile=kernel32Mapping.NewProc("MapViewOfFile")
var unmapViewOfFile=kernel32Mapping.NewProc("UnmapViewOfFile")
var closeMapHandle=kernel32Mapping.NewProc("CloseHandle")
var rtlMoveMemory=syscall.NewLazyDLL("ntdll.dll").NewProc("RtlMoveMemory")
const pageReadonly=0x02
const fileMapRead=0x0004

type windowsMapping struct{
	handle uintptr
	view uintptr
	size int
	scratch []byte
}
func mapFile(f *os.File,n int)(mappedRegion,error){
	m,_,e:=createFileMapping.Call(f.Fd(),0,pageReadonly,0,0,0)
	if m==0{return nil,fmt.Errorf("CreateFileMappingW: %v",e)}
	view,_,vErr:=mapViewOfFile.Call(m,fileMapRead,0,0,0)
	if view==0{closeMapHandle.Call(m);return nil,fmt.Errorf("MapViewOfFile: %v",vErr)}
	return &windowsMapping{handle:m,view:view,size:n,scratch:make([]byte,blockSize)},nil
}
func(m *windowsMapping)ReadBlock(off int64)([]byte,error){
	if off<0 || off+blockSize>int64(m.size){return nil,fmt.Errorf("invalid mapped offset %d",off)}
	// MapViewOfFile returns a Win32 address (uintptr), not a Go-owned pointer.
	// Copy through an OS-provided native routine; do not cast arbitrary uintptr into unsafe.Pointer.
	// This charges a bounded 64-KiB user buffer to the MMAP control.
	_,_,e:=rtlMoveMemory.Call(uintptr(unsafe.Pointer(&m.scratch[0])),m.view+uintptr(off),blockSize)
	if e!=nil && e!=syscall.Errno(0){return nil,fmt.Errorf("RtlMoveMemory: %v",e)}
	return m.scratch,nil
}
func(m *windowsMapping)Close()error{
	a,_,e:=unmapViewOfFile.Call(m.view)
	closeMapHandle.Call(m.handle)
	if a==0{return fmt.Errorf("UnmapViewOfFile: %v",e)}
	return nil
}
