package main

import (
 "encoding/binary"
 "errors"
 "hash"
 "math"
)

const (
 dimension = 128
 rankCap = 16
 episodes = 32
 vectorsPerEpisode = 128
 schema = "forge.acc45.original-u22.lowrank.nativego.v1"
)
var seeds = []uint64{94101,94103,94107,94109,94111}
var cohorts = []string{"RANK8","RANK24","FULL_RANDOM"}
var modes = []string{"DENSE","TILED","CSR","LOWRANK16"}

func mix(x uint64) uint64 {
 x+=0x9e3779b97f4a7c15
 x=(x^(x>>30))*0xbf58476d1ce4e5b9
 x=(x^(x>>27))*0x94d049bb133111eb
 return x^(x>>31)
}
func randomFloat(x uint64) float64 {
 return (float64(mix(x)>>11)*(1.0/9007199254740992.0))*2-1
}
func oneOf(xs []string, s string) bool {
 for _,v:=range xs {if s==v{return true}}
 return false
}
func makeMatrix(cohort string, seed uint64, episode int)([]float64,error) {
 if !oneOf(cohorts,cohort) {return nil,errors.New("unknown source cohort")}
 base:=mix(seed^uint64(episode)*0x9e3779b97f4a7c15^0x55e97a2403bc819d)
 m:=make([]float64,dimension*dimension)
 if cohort=="FULL_RANDOM" {
  for i:=range m {m[i]=randomFloat(base^uint64(i)*0x713889a22b9346d3)}
  return m,nil
 }
 rank:=8
 if cohort=="RANK24"{rank=24}
 u:=make([]float64,dimension*rank)
 v:=make([]float64,rank*dimension)
 for i:=0;i<dimension;i++{
  for k:=0;k<rank;k++{
   u[i*rank+k]=randomFloat(base^0xb18b92bfa6e8f503^uint64(i)*0x1692e7481ad4cdef^uint64(k)*0x73f765a8ed3c1089)
  }
 }
 for k:=0;k<rank;k++{
  for j:=0;j<dimension;j++{
   v[k*dimension+j]=randomFloat(base^0xc39953fd9de33adb^uint64(k)*0x253fc8de6e6f9b73^uint64(j)*0xd164a183ce28b1c5)
  }
 }
 for i:=0;i<dimension;i++{
  for j:=0;j<dimension;j++{
   sum:=0.0
   for k:=0;k<rank;k++ {sum+=u[i*rank+k]*v[k*dimension+j]}
   m[i*dimension+j]=sum/math.Sqrt(float64(rank))
  }
 }
 return m,nil
}
func makeVector(seed uint64, episode,query int) []float64 {
 b:=mix(seed^0x420f785e9539cbab^uint64(episode)*0x9e3779b97f4a7c15^uint64(query)*0x76ddf4b7e5cebd15)
 x:=make([]float64,dimension)
 for i:=range x {x[i]=randomFloat(b^uint64(i)*0xa92fc38de31b70d5)}
 return x
}
func digestFloat(h hash.Hash, v float64) {
 var b [8]byte
 binary.LittleEndian.PutUint64(b[:],math.Float64bits(v))
 _,_=h.Write(b[:])
}
func digestArray(h hash.Hash, a []float64) {
 for _,v:=range a {digestFloat(h,v)}
}
