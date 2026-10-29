//go:build linux
package main
import("os";"syscall";"errors")
func mapFile(f *os.File,n int)([]byte,error){return syscall.Mmap(int(f.Fd()),0,n,syscall.PROT_READ,syscall.MAP_SHARED)}
func unmapFile(b []byte)error{if len(b)==0{return errors.New("empty mapping")};return syscall.Munmap(b)}
