// Package devroles is the frozen F102-O TRAIN-only template translator.
// No answers, actual QA evaluation, model inference, or scientific authority.
package devroles

import (
 "strings"
 "unicode"
 "unicode/utf8"
 "github.com/spoonman136668-ai/forge/noveltymechanisms/langroles"
 "github.com/spoonman136668-ai/forge/noveltymechanisms/largegraph"
)
type mapping struct { shape string; hops int; steps []largegraph.Step }
var frozenTrainTemplates = []mapping{
	{shape:"the actor of [] also starred in which movies",hops:2,steps:[]largegraph.Step{{Role:"starred_actors",Direction:largegraph.Forward},{Role:"starred_actors",Direction:largegraph.Reverse}}},
	{shape:"which movies share the same actor of []",hops:2,steps:[]largegraph.Step{{Role:"starred_actors",Direction:largegraph.Forward},{Role:"starred_actors",Direction:largegraph.Reverse}}},
	{shape:"which movies have the same director of []",hops:2,steps:[]largegraph.Step{{Role:"directed_by",Direction:largegraph.Forward},{Role:"directed_by",Direction:largegraph.Reverse}}},
	{shape:"which films have the same director of []",hops:2,steps:[]largegraph.Step{{Role:"directed_by",Direction:largegraph.Forward},{Role:"directed_by",Direction:largegraph.Reverse}}},
	{shape:"the actor of [] also starred in which films",hops:2,steps:[]largegraph.Step{{Role:"starred_actors",Direction:largegraph.Forward},{Role:"starred_actors",Direction:largegraph.Reverse}}},
	{shape:"what are the films that have the same actor of []",hops:2,steps:[]largegraph.Step{{Role:"starred_actors",Direction:largegraph.Forward},{Role:"starred_actors",Direction:largegraph.Reverse}}},
	{shape:"the director of [] is also the director of which movies",hops:2,steps:[]largegraph.Step{{Role:"directed_by",Direction:largegraph.Forward},{Role:"directed_by",Direction:largegraph.Reverse}}},
	{shape:"which films share the same director of []",hops:2,steps:[]largegraph.Step{{Role:"directed_by",Direction:largegraph.Forward},{Role:"directed_by",Direction:largegraph.Reverse}}},
	{shape:"which films have the same actor of []",hops:2,steps:[]largegraph.Step{{Role:"starred_actors",Direction:largegraph.Forward},{Role:"starred_actors",Direction:largegraph.Reverse}}},
	{shape:"which films share the same actor of []",hops:2,steps:[]largegraph.Step{{Role:"starred_actors",Direction:largegraph.Forward},{Role:"starred_actors",Direction:largegraph.Reverse}}},
	{shape:"the director of [] also directed which films",hops:2,steps:[]largegraph.Step{{Role:"directed_by",Direction:largegraph.Forward},{Role:"directed_by",Direction:largegraph.Reverse}}},
	{shape:"the actor in [] also appears in which films",hops:2,steps:[]largegraph.Step{{Role:"starred_actors",Direction:largegraph.Forward},{Role:"starred_actors",Direction:largegraph.Reverse}}},
	{shape:"the director of [] is also the director of which films",hops:2,steps:[]largegraph.Step{{Role:"directed_by",Direction:largegraph.Forward},{Role:"directed_by",Direction:largegraph.Reverse}}},
	{shape:"what are the movies that have the same actor of []",hops:2,steps:[]largegraph.Step{{Role:"starred_actors",Direction:largegraph.Forward},{Role:"starred_actors",Direction:largegraph.Reverse}}},
	{shape:"the actor in [] also appears in which movies",hops:2,steps:[]largegraph.Step{{Role:"starred_actors",Direction:largegraph.Forward},{Role:"starred_actors",Direction:largegraph.Reverse}}},
	{shape:"what are the films that are directed by the same director of []",hops:2,steps:[]largegraph.Step{{Role:"directed_by",Direction:largegraph.Forward},{Role:"directed_by",Direction:largegraph.Reverse}}},
	{shape:"the director of [] also directed which movies",hops:2,steps:[]largegraph.Step{{Role:"directed_by",Direction:largegraph.Forward},{Role:"directed_by",Direction:largegraph.Reverse}}},
	{shape:"what are the movies that are directed by the same director of []",hops:2,steps:[]largegraph.Step{{Role:"directed_by",Direction:largegraph.Forward},{Role:"directed_by",Direction:largegraph.Reverse}}},
	{shape:"the actor [] is a co-star of who",hops:2,steps:[]largegraph.Step{{Role:"starred_actors",Direction:largegraph.Reverse},{Role:"starred_actors",Direction:largegraph.Forward}}},
	{shape:"the actor [] acted together with who",hops:2,steps:[]largegraph.Step{{Role:"starred_actors",Direction:largegraph.Reverse},{Role:"starred_actors",Direction:largegraph.Forward}}},
	{shape:"which person directed the movies starred by the actors in []",hops:3,steps:[]largegraph.Step{{Role:"starred_actors",Direction:largegraph.Forward},{Role:"starred_actors",Direction:largegraph.Reverse},{Role:"directed_by",Direction:largegraph.Forward}}},
	{shape:"who directed movies that share actors with the movie []",hops:3,steps:[]largegraph.Step{{Role:"starred_actors",Direction:largegraph.Forward},{Role:"starred_actors",Direction:largegraph.Reverse},{Role:"directed_by",Direction:largegraph.Forward}}},
	{shape:"who is listed as screenwriter of the films starred by [] actors",hops:3,steps:[]largegraph.Step{{Role:"starred_actors",Direction:largegraph.Forward},{Role:"starred_actors",Direction:largegraph.Reverse},{Role:"written_by",Direction:largegraph.Forward}}},
	{shape:"what types are the movies starred by actors in []",hops:3,steps:[]largegraph.Step{{Role:"starred_actors",Direction:largegraph.Forward},{Role:"starred_actors",Direction:largegraph.Reverse},{Role:"has_genre",Direction:largegraph.Forward}}},
	{shape:"which person wrote the films directed by the director of []",hops:3,steps:[]largegraph.Step{{Role:"directed_by",Direction:largegraph.Forward},{Role:"directed_by",Direction:largegraph.Reverse},{Role:"written_by",Direction:largegraph.Forward}}},
	{shape:"the movies that share actors with the movie [] are directed by who",hops:3,steps:[]largegraph.Step{{Role:"starred_actors",Direction:largegraph.Forward},{Role:"starred_actors",Direction:largegraph.Reverse},{Role:"directed_by",Direction:largegraph.Forward}}},
	{shape:"which person directed the films acted by the actors in []",hops:3,steps:[]largegraph.Step{{Role:"starred_actors",Direction:largegraph.Forward},{Role:"starred_actors",Direction:largegraph.Reverse},{Role:"directed_by",Direction:largegraph.Forward}}},
	{shape:"who are the writers that the actors in their films also appear in the film []",hops:3,steps:[]largegraph.Step{{Role:"starred_actors",Direction:largegraph.Forward},{Role:"starred_actors",Direction:largegraph.Reverse},{Role:"written_by",Direction:largegraph.Forward}}},
	{shape:"who are the directors that the actors in their films also appear in the film []",hops:3,steps:[]largegraph.Step{{Role:"starred_actors",Direction:largegraph.Forward},{Role:"starred_actors",Direction:largegraph.Reverse},{Role:"directed_by",Direction:largegraph.Forward}}},
	{shape:"what are the genres of the films whose actors also appear in []",hops:3,steps:[]largegraph.Step{{Role:"starred_actors",Direction:largegraph.Forward},{Role:"starred_actors",Direction:largegraph.Reverse},{Role:"has_genre",Direction:largegraph.Forward}}},
	{shape:"who are the directors that the actors in their movies also appear in the movie []",hops:3,steps:[]largegraph.Step{{Role:"starred_actors",Direction:largegraph.Forward},{Role:"starred_actors",Direction:largegraph.Reverse},{Role:"directed_by",Direction:largegraph.Forward}}},
	{shape:"what types are the films starred by actors in []",hops:3,steps:[]largegraph.Step{{Role:"starred_actors",Direction:largegraph.Forward},{Role:"starred_actors",Direction:largegraph.Reverse},{Role:"has_genre",Direction:largegraph.Forward}}},
	{shape:"what genres do the films that share actors with [] fall under",hops:3,steps:[]largegraph.Step{{Role:"starred_actors",Direction:largegraph.Forward},{Role:"starred_actors",Direction:largegraph.Reverse},{Role:"has_genre",Direction:largegraph.Forward}}},
	{shape:"what are the genres of the movies whose actors also appear in []",hops:3,steps:[]largegraph.Step{{Role:"starred_actors",Direction:largegraph.Forward},{Role:"starred_actors",Direction:largegraph.Reverse},{Role:"has_genre",Direction:largegraph.Forward}}},
	{shape:"who is listed as screenwriter of the movies directed by the [] director",hops:3,steps:[]largegraph.Step{{Role:"directed_by",Direction:largegraph.Forward},{Role:"directed_by",Direction:largegraph.Reverse},{Role:"written_by",Direction:largegraph.Forward}}},
	{shape:"the films that share actors with the film [] are written by who",hops:3,steps:[]largegraph.Step{{Role:"starred_actors",Direction:largegraph.Forward},{Role:"starred_actors",Direction:largegraph.Reverse},{Role:"written_by",Direction:largegraph.Forward}}},
	{shape:"the films that share directors with the films [] are written by who",hops:3,steps:[]largegraph.Step{{Role:"directed_by",Direction:largegraph.Forward},{Role:"directed_by",Direction:largegraph.Reverse},{Role:"written_by",Direction:largegraph.Forward}}},
	{shape:"who is listed as director of the films starred by [] actors",hops:3,steps:[]largegraph.Step{{Role:"starred_actors",Direction:largegraph.Forward},{Role:"starred_actors",Direction:largegraph.Reverse},{Role:"directed_by",Direction:largegraph.Forward}}},
	{shape:"who starred movies for the director of []",hops:3,steps:[]largegraph.Step{{Role:"directed_by",Direction:largegraph.Forward},{Role:"directed_by",Direction:largegraph.Reverse},{Role:"starred_actors",Direction:largegraph.Forward}}},
	{shape:"who wrote films that share actors with the film []",hops:3,steps:[]largegraph.Step{{Role:"starred_actors",Direction:largegraph.Forward},{Role:"starred_actors",Direction:largegraph.Reverse},{Role:"written_by",Direction:largegraph.Forward}}},
	{shape:"who is listed as screenwriter of the movies starred by [] actors",hops:3,steps:[]largegraph.Step{{Role:"starred_actors",Direction:largegraph.Forward},{Role:"starred_actors",Direction:largegraph.Reverse},{Role:"written_by",Direction:largegraph.Forward}}},
	{shape:"who is listed as director of the movies starred by [] actors",hops:3,steps:[]largegraph.Step{{Role:"starred_actors",Direction:largegraph.Forward},{Role:"starred_actors",Direction:largegraph.Reverse},{Role:"directed_by",Direction:largegraph.Forward}}},
	{shape:"the movies that share actors with the movie [] are written by who",hops:3,steps:[]largegraph.Step{{Role:"starred_actors",Direction:largegraph.Forward},{Role:"starred_actors",Direction:largegraph.Reverse},{Role:"written_by",Direction:largegraph.Forward}}},
	{shape:"the movies that share actors with the movie [] were in which genres",hops:3,steps:[]largegraph.Step{{Role:"starred_actors",Direction:largegraph.Forward},{Role:"starred_actors",Direction:largegraph.Reverse},{Role:"has_genre",Direction:largegraph.Forward}}},
	{shape:"what genres are the films starred by [] actors",hops:3,steps:[]largegraph.Step{{Role:"starred_actors",Direction:largegraph.Forward},{Role:"starred_actors",Direction:largegraph.Reverse},{Role:"has_genre",Direction:largegraph.Forward}}},
	{shape:"what genres do the movies that share actors with [] fall under",hops:3,steps:[]largegraph.Step{{Role:"starred_actors",Direction:largegraph.Forward},{Role:"starred_actors",Direction:largegraph.Reverse},{Role:"has_genre",Direction:largegraph.Forward}}},
}
func validQuestion(q string,hops int)(string,string,langroles.Reason){
 if len(q)==0||len(q)>1024||!utf8.ValidString(q)||(hops!=2&&hops!=3){return "","",langroles.ReasonMalformed}
 for _,r:=range q {if unicode.IsControl(r){return "","",langroles.ReasonMalformed}}
 i:=strings.IndexByte(q,'[');j:=strings.IndexByte(q,']')
 if i<0||j<=i+1||strings.Count(q,"[")!=1||strings.Count(q,"]")!=1 {return "","",langroles.ReasonMalformed}
 root:=q[i+1:j]
 if len(root)==0||len(root)>512||root!=strings.TrimSpace(root) {return "","",langroles.ReasonTopic}
 shape:=q[:i]+"[]"+q[j+1:]
 if strings.HasSuffix(shape,"?")||strings.HasSuffix(shape,"."){shape=shape[:len(shape)-1]}
 grammar:=[]byte(shape)
 for n:=range grammar {if grammar[n]>='A'&&grammar[n]<='Z'{grammar[n]+='a'-'A'}}
 return root,string(grammar),langroles.ReasonNone
}
// Parse delegates F101 positive rules unchanged and otherwise uses the frozen
// train-only template table. No invalid input returns source root or steps.
func Parse(question string,hops int)langroles.Result{
 root,shape,reason:=validQuestion(question,hops)
 if reason!=langroles.ReasonNone{return langroles.Result{Status:langroles.Abstained,Reason:reason}}
 old:=langroles.Parse(question,hops)
 if old.Status==langroles.Matched {
  steps:=make([]largegraph.Step,len(old.Steps));copy(steps,old.Steps)
  return langroles.Result{Status:langroles.Matched,Root:old.Root,Steps:steps}
 }
 for _,t:=range frozenTrainTemplates{
  if shape!=t.shape {continue}
  if hops!=t.hops{return langroles.Result{Status:langroles.Abstained,Reason:langroles.ReasonHopMismatch}}
  steps:=make([]largegraph.Step,len(t.steps));copy(steps,t.steps)
  return langroles.Result{Status:langroles.Matched,Root:root,Steps:steps}
 }
 if old.Reason==langroles.ReasonHopMismatch{return langroles.Result{Status:langroles.Abstained,Reason:langroles.ReasonHopMismatch}}
 return langroles.Result{Status:langroles.Abstained,Reason:langroles.ReasonUnsupported}
}
