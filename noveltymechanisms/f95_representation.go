// Package noveltymechanisms prototypes an unaccepted, trainable-future
// relation-composition representation. It is source engineering, not a
// qualified Wingless/Yggdrasil science result or deployed model.
package noveltymechanisms

import (
 "errors"
 "sort"
)

var ErrModel=errors.New("FORGE_F95_UNQUALIFIED_RELATIONAL_IMPLEMENTATION")
type Relation struct {
 From string
 Role string
 To string
}
type Memory struct {
 edges map[string]map[string][]string
 count int
}
func f95Name(s string)bool{
 if len(s)<1||len(s)>48{return false}
 for _,r:=range s{
  if !((r>='a'&&r<='z')||(r>='0'&&r<='9')||r=='-'||r=='_'){return false}
 }
 return true
}
// Compile stores typed relation edges; target identities are not merged just
// because two entities share a role. Unlike environment-vector perturbation,
// its source representation can express variable-binding paths.
func Compile(relations []Relation)(Memory,error){
 var zero Memory
 if len(relations)<1||len(relations)>128{return zero,ErrModel}
 graph:=make(map[string]map[string][]string)
 used:=make(map[Relation]bool)
 for _,r:=range relations{
  if !f95Name(r.From)||!f95Name(r.Role)||!f95Name(r.To)||
   r.From==r.To||used[r]{return zero,ErrModel}
  used[r]=true
  if graph[r.From]==nil{graph[r.From]=map[string][]string{}}
  graph[r.From][r.Role]=append(graph[r.From][r.Role],r.To)
 }
 for _,roles:=range graph{
  for role,targets:=range roles{
   sort.Strings(targets)
   roles[role]=targets
  }
 }
 return Memory{edges:graph,count:len(relations)},nil
}
func (m Memory) RelationCount()int{return m.count}
