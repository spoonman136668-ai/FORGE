package main

import (
 "errors"
 "math"
)
type lowRank struct {
 U [dimension*rankCap]float64
 V [rankCap*dimension]float64
 Rank int
}
type csr struct {
 Rows [dimension+1]int
 Columns []uint16
 Values []float64
}
type representation struct {
 Mode string
 Dense []float64
 Sparse csr
 Factor lowRank
}
func decomposeACA(input []float64) (lowRank,error) {
 var f lowRank
 if len(input)!=dimension*dimension{return f,errors.New("incorrect matrix size")}
 residual:=append([]float64(nil),input...)
 initial:=0.0
 for _,v:=range residual{
  if math.IsNaN(v)||math.IsInf(v,0){return f,errors.New("nonfinite matrix")}
  if a:=math.Abs(v);a>initial{initial=a}
 }
 if initial==0{return f,nil}
 for r:=0;r<rankCap;r++{
  maximum:=0.0;index:=0
  for i,v:=range residual{
   if a:=math.Abs(v);a>maximum {maximum=a;index=i}
  }
  if maximum<=1e-12*initial{break}
  p:=index/dimension;q:=index%dimension
  pivot:=residual[index]
  for i:=0;i<dimension;i++{f.U[i*rankCap+r]=residual[i*dimension+q]/pivot}
  for j:=0;j<dimension;j++{f.V[r*dimension+j]=residual[p*dimension+j]}
  for i:=0;i<dimension;i++{
   for j:=0;j<dimension;j++{
    residual[i*dimension+j]-=f.U[i*rankCap+r]*f.V[r*dimension+j]
   }
  }
  f.Rank++
 }
 return f,nil
}
func prepare(mode string, matrix []float64)(representation,error){
 var p representation
 if !oneOf(modes,mode)||len(matrix)!=dimension*dimension{return p,errors.New("invalid mode or public matrix")}
 p.Mode=mode
 switch mode{
 case "DENSE","TILED":
  p.Dense=append([]float64(nil),matrix...)
 case "CSR":
  p.Sparse.Columns=make([]uint16,0,len(matrix))
  p.Sparse.Values=make([]float64,0,len(matrix))
  for i:=0;i<dimension;i++{
   p.Sparse.Rows[i]=len(p.Sparse.Values)
   for j:=0;j<dimension;j++{
    v:=matrix[i*dimension+j]
    if v!=0{
     p.Sparse.Columns=append(p.Sparse.Columns,uint16(j))
     p.Sparse.Values=append(p.Sparse.Values,v)
    }
   }
  }
  p.Sparse.Rows[dimension]=len(p.Sparse.Values)
 case "LOWRANK16":
  f,err:=decomposeACA(matrix)
  if err!=nil{return p,err}
  p.Factor=f
 }
 return p,nil
}
func (p representation)LogicalBytes() int {
 switch p.Mode {
 case "LOWRANK16":return 2*dimension*rankCap*8
 case "CSR":return len(p.Sparse.Columns)*2+len(p.Sparse.Values)*8+(dimension+1)*8
 default:return dimension*dimension*8
 }
}
func denseMul(matrix,x []float64)[]float64 {
 y:=make([]float64,dimension)
 for i:=0;i<dimension;i++{
  sum:=0.0
  for j:=0;j<dimension;j++{sum+=matrix[i*dimension+j]*x[j]}
  y[i]=sum
 }
 return y
}
func (p representation)Apply(x []float64)([]float64,error) {
 if len(x)!=dimension{return nil,errors.New("invalid input vector")}
 y:=make([]float64,dimension)
 switch p.Mode {
 case "DENSE":
  return denseMul(p.Dense,x),nil
 case "TILED":
  for i:=0;i<dimension;i++{
   sum:=0.0
   for col:=0;col<dimension;col+=16{
    for j:=col;j<col+16;j++{sum+=p.Dense[i*dimension+j]*x[j]}
   }
   y[i]=sum
  }
 case "CSR":
  for i:=0;i<dimension;i++{
   sum:=0.0
   for k:=p.Sparse.Rows[i];k<p.Sparse.Rows[i+1];k++{sum+=p.Sparse.Values[k]*x[p.Sparse.Columns[k]]}
   y[i]=sum
  }
 case "LOWRANK16":
  var tmp [rankCap]float64
  for r:=0;r<p.Factor.Rank;r++{
   sum:=0.0
   for j:=0;j<dimension;j++{sum+=p.Factor.V[r*dimension+j]*x[j]}
   tmp[r]=sum
  }
  for i:=0;i<dimension;i++{
   sum:=0.0
   for r:=0;r<p.Factor.Rank;r++{sum+=p.Factor.U[i*rankCap+r]*tmp[r]}
   y[i]=sum
  }
 default:return nil,errors.New("unknown representation")
 }
 return y,nil
}
