//go:build linux

package main

import (
	"os"
	"syscall"
)

type mappedRegion interface {
	ReadBlock(off int64)([]byte,error)
	Close()error
}
type linuxMapping struct{ data []byte }
func mapFile(f *os.File,n int)(mappedRegion,error){
	b,err:=syscall.Mmap(int(f.Fd()),0,n,syscall.PROT_READ,syscall.MAP_SHARED)
	if err!=nil{return nil,err}
	return &linuxMapping{data:b},nil
}
func(m *linuxMapping)ReadBlock(off int64)([]byte,error){return m.data[int(off):int(off)+blockSize],nil}
func(m *linuxMapping)Close()error{return syscall.Munmap(m.data)}
