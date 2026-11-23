package noveltymechanisms

import "sort"

// Resolution is a bounded set of typed binding endpoints, never a scientific
// prediction or a model evaluation score.
type Resolution struct {
 Targets []string
 TraversedRoles int
 CandidatePaths int
 UniqueAnswer bool
}
// Resolve walks the role sequence exactly. Unrelated edges cannot substitute
// for a requested role; competing paths are preserved as ambiguity rather
// than optimistically collapsed to the first or memorized endpoint.
func Resolve(m Memory,root string,roles []string)(Resolution,error){
 var zero Resolution
 if !f95Name(root)||len(roles)<1||len(roles)>8||
  m.edges==nil||m.count<1{return zero,ErrModel}
 current:=map[string]bool{root:true}
 for _,role:=range roles{
  if !f95Name(role){return zero,ErrModel}
  next:=make(map[string]bool)
  for node:=range current{
   for _,target:=range m.edges[node][role]{
    next[target]=true
    if len(next)>128{return zero,ErrModel}
   }
  }
  if len(next)==0{return Resolution{TraversedRoles:len(roles)},nil}
  current=next
 }
 targets:=make([]string,0,len(current))
 for node:=range current{targets=append(targets,node)}
 sort.Strings(targets)
 return Resolution{Targets:targets,TraversedRoles:len(roles),
  CandidatePaths:len(targets),UniqueAnswer:len(targets)==1},nil
}
// Verify never upgrades an ambiguous endpoint to an accepted result.
func Verify(m Memory,root string,roles []string,expected string)(bool,error){
 if !f95Name(expected){return false,ErrModel}
 result,err:=Resolve(m,root,roles)
 if err!=nil{return false,err}
 return result.UniqueAnswer&&result.Targets[0]==expected,nil
}
