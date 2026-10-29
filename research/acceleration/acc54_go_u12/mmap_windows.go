//go:build windows
package main
import("os";"errors";"syscall";"unsafe")
var k= syscall.NewLazyDLL("kernel32.dll")
var createMapping=k.NewProc("CreateFileMappingW")
var mapView=k.NewProc("MapViewOfFile")
var unmapView=k.NewProc("UnmapViewOfFile")
var closeHandle=k.NewProc("CloseHandle")
func mapFile(f *os.File,n int)([]byte,error){
 h,_,e:=createMapping.Call(f.Fd(),0,2,0,0,0)
 if h==0{return nil,e}
 addr,_,err:=mapView.Call(h,4,0,0,uintptr(n));closeHandle.Call(h)
 if addr==0{return nil,err}
 return unsafe.Slice((*byte)(unsafe.Pointer(addr)),n),nil
}
func unmapFile(b []byte)error{
 if len(b)==0{return errors.New("empty mapping")}
 ret,_,e:=unmapView.Call(uintptr(unsafe.Pointer(&b[0])));if ret==0{return e};return nil
}
