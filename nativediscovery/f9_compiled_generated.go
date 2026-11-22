// Code generated from FORGE F6's fixed grammar for F9 DEV qualification.
// Bounded, checked-in, compiled as part of original Go regression; NOT activated.
package nativediscovery
type f9CompiledConstantPositive struct { f3Core }
func (m *f9CompiledConstantPositive) Predict(c f2Context) int {
 if c.Regime<0||c.Regime>1||c.Cue<0||c.Cue>3||c.Mode<0||c.Mode>1{return 1}
 if direct,seen:=f2major(m.Counts[c.Regime][c.Cue][c.Mode]);seen{return direct}
 sign:=1
 if false {sign= -sign}
 return sign
}
type f9CompiledConstantNegative struct { f3Core }
func (m *f9CompiledConstantNegative) Predict(c f2Context) int {
 if c.Regime<0||c.Regime>1||c.Cue<0||c.Cue>3||c.Mode<0||c.Mode>1{return 1}
 if direct,seen:=f2major(m.Counts[c.Regime][c.Cue][c.Mode]);seen{return direct}
 sign:=-1
 if false {sign= -sign}
 return sign
}
type f9CompiledCueParityPositive struct { f3Core }
func (m *f9CompiledCueParityPositive) Predict(c f2Context) int {
 if c.Regime<0||c.Regime>1||c.Cue<0||c.Cue>3||c.Mode<0||c.Mode>1{return 1}
 if direct,seen:=f2major(m.Counts[c.Regime][c.Cue][c.Mode]);seen{return direct}
 sign:=1
 if c.Cue%2==1 {sign= -sign}
 return sign
}
type f9CompiledCueParityNegative struct { f3Core }
func (m *f9CompiledCueParityNegative) Predict(c f2Context) int {
 if c.Regime<0||c.Regime>1||c.Cue<0||c.Cue>3||c.Mode<0||c.Mode>1{return 1}
 if direct,seen:=f2major(m.Counts[c.Regime][c.Cue][c.Mode]);seen{return direct}
 sign:=-1
 if c.Cue%2==1 {sign= -sign}
 return sign
}
type f9CompiledModeParityPositive struct { f3Core }
func (m *f9CompiledModeParityPositive) Predict(c f2Context) int {
 if c.Regime<0||c.Regime>1||c.Cue<0||c.Cue>3||c.Mode<0||c.Mode>1{return 1}
 if direct,seen:=f2major(m.Counts[c.Regime][c.Cue][c.Mode]);seen{return direct}
 sign:=1
 if c.Mode==1 {sign= -sign}
 return sign
}
type f9CompiledModeParityNegative struct { f3Core }
func (m *f9CompiledModeParityNegative) Predict(c f2Context) int {
 if c.Regime<0||c.Regime>1||c.Cue<0||c.Cue>3||c.Mode<0||c.Mode>1{return 1}
 if direct,seen:=f2major(m.Counts[c.Regime][c.Cue][c.Mode]);seen{return direct}
 sign:=-1
 if c.Mode==1 {sign= -sign}
 return sign
}
type f9CompiledCueModeXorPositive struct { f3Core }
func (m *f9CompiledCueModeXorPositive) Predict(c f2Context) int {
 if c.Regime<0||c.Regime>1||c.Cue<0||c.Cue>3||c.Mode<0||c.Mode>1{return 1}
 if direct,seen:=f2major(m.Counts[c.Regime][c.Cue][c.Mode]);seen{return direct}
 sign:=1
 if c.Cue%2!=(c.Mode%2) {sign= -sign}
 return sign
}
type f9CompiledCueModeXorNegative struct { f3Core }
func (m *f9CompiledCueModeXorNegative) Predict(c f2Context) int {
 if c.Regime<0||c.Regime>1||c.Cue<0||c.Cue>3||c.Mode<0||c.Mode>1{return 1}
 if direct,seen:=f2major(m.Counts[c.Regime][c.Cue][c.Mode]);seen{return direct}
 sign:=-1
 if c.Cue%2!=(c.Mode%2) {sign= -sign}
 return sign
}
