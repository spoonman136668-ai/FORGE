//go:build windows

package main

import (
	"fmt"
	"os"
	"syscall"
	"unsafe"
)
var kernel32Mapping=syscall.NewLazyDLL("kernel32.dll")
var createFileMapping=kernel32Mapping.NewProc("CreateFileMappingW")
var mapViewOfFile=kernel32Mapping.NewProc("MapViewOfFile")
var unmapViewOfFile=kernel32Mapping.NewProc("UnmapViewOfFile")
var closeMapHandle=kernel32Mapping.NewProc("CloseHandle")
const pageReadonly=0x02
const fileMapRead=0x0004
var mappingHandles=map[uintptr]uintptr{}
func mapFile(f *os.File,n int)([]byte,error){
	m,_,e:=createFileMapping.Call(f.Fd(),0,pageReadonly,0,0,0)
	if m==0{return nil,fmt.Errorf("CreateFileMappingW: %v",e)}
	view,_,vErr:=mapViewOfFile.Call(m,fileMapRead,0,0,0)
	if view==0{closeMapHandle.Call(m);return nil,fmt.Errorf("MapViewOfFile: %v",vErr)}
	mappingHandles[view]=m
	return unsafe.Slice((*byte)(unsafe.Pointer(view)),n),nil
}
func unmapFile(b []byte)error{
	if len(b)==0{return nil}
	ptr:=uintptr(unsafe.Pointer(&b[0]))
	handle,ok:=mappingHandles[ptr];if !ok{return fmt.Errorf("missing mmap handle")}
	delete(mappingHandles,ptr)
	a,_,e:=unmapViewOfFile.Call(ptr)
	closeMapHandle.Call(handle)
	if a==0{return fmt.Errorf("UnmapViewOfFile: %v",e)}
	return nil
}
