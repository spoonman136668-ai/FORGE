package main

import (
	"crypto/sha256"
	"encoding/binary"
	"encoding/hex"
	"errors"
	"fmt"
	"io"
	"math/bits"
	"os"
)

const blockSize = 64 * 1024
const rssBudget = 64 * 1024 * 1024
const bufferBudget = 16 * 1024 * 1024
const schema = "forge.acc40.original-u12-native-go-outofcore.v1"

var modes = []string{"RESIDENT", "SYNC", "MMAP", "STATIC", "PREDICTIVE"}
var schedules = []string{"SEQUENTIAL", "STRIDED", "SHUFFLED"}
var trialSeeds = []uint64{49101, 49103, 49107, 49109, 49111}

func splitmix(x uint64) uint64 {
	x += 0x9e3779b97f4a7c15
	x = (x ^ x >> 30) * 0xbf58476d1ce4e5b9
	x = (x ^ x >> 27) * 0x94d049bb133111eb
	return x ^ x >> 31
}
func blockBytes(index int, dst []byte) {
	for j := 0; j < len(dst); j += 8 {
		v := splitmix(uint64(index)*0x2545f4914f6cdd1d + uint64(j/8) + 271828)
		binary.LittleEndian.PutUint64(dst[j:j+8], v)
	}
}
func makeSource(path string, size int64) (string, error) {
	if size <= 0 || size%blockSize != 0 { return "", fmt.Errorf("invalid source size %d", size) }
	f, err := os.Create(path); if err != nil { return "", err }
	h := sha256.New(); buf := make([]byte, blockSize)
	for i := int64(0); i < size/blockSize; i++ {
		blockBytes(int(i), buf)
		if _,err= f.Write(buf); err!=nil { f.Close();return "",err }
		_,_ = h.Write(buf)
	}
	if err=f.Sync(); err!=nil {f.Close();return "",err}
	if err=f.Close(); err!=nil{return "",err}
	return hex.EncodeToString(h.Sum(nil)),nil
}
func scheduleFor(name string, n int, seed uint64) ([]int,error) {
	if n<2{return nil,errors.New("schedule needs at least 2 blocks")}
	v := make([]int,n)
	for i:=range v {v[i]=i}
	switch name {
	case "SEQUENTIAL":
	case "STRIDED":
		step:=17
		for gcd(step,n)!=1 {step+=2}
		for i:=range v {v[i]=(i*step)%n}
	case "SHUFFLED":
		x:=seed
		for i:=n-1;i>0;i-- {
			x=splitmix(x)
			j:=int(x%uint64(i+1))
			v[i],v[j]=v[j],v[i]
		}
	default:return nil,fmt.Errorf("unknown schedule %q",name)
	}
	return v,nil
}
func gcd(a,b int)int{for b!=0{a,b=b,a%b};return a}

type pendingRead struct {
	offset int64
	done chan struct{}
	n int
	err error
}
type blockReader struct {
	file *os.File
	mode string
	size int64
	mapped []byte
	resident []byte
	current []byte
	ahead []byte
	pending *pendingRead
	seen int
	prevIndex int
	lastDelta int
	readBytes int64
	prefetchedBytes int64
	wastedBytes int64
	hits int64
}
func newBlockReader(f *os.File,mode string,size int64)(*blockReader,error){
	r:=&blockReader{file:f,mode:mode,size:size}
	switch mode {
	case "RESIDENT":
		b,e:=io.ReadAll(f);if e!=nil{return nil,e}
		if int64(len(b))!=size{return nil,io.ErrUnexpectedEOF}
		r.resident=b;r.readBytes=int64(len(b))
	case "MMAP":
		b,e:=mapFile(f,int(size));if e!=nil{return nil,e};r.mapped=b
	case "SYNC","STATIC","PREDICTIVE":
		r.current=make([]byte,blockSize)
		if mode!="SYNC"{r.ahead=make([]byte,blockSize)}
	default:return nil,fmt.Errorf("unknown mode %q",mode)
	}
	return r,nil
}
func (r *blockReader) settle(requestOffset int64,consume bool)(bool,error){
	if r.pending==nil{return false,nil}
	p:=r.pending
	<-p.done
	r.pending=nil
	r.readBytes+=int64(p.n)
	r.prefetchedBytes+=int64(p.n)
	if p.err!=nil{return false,p.err}
	if p.n!=blockSize{return false,io.ErrUnexpectedEOF}
	if consume && p.offset==requestOffset {
		r.hits++
		r.current,r.ahead=r.ahead,r.current
		return true,nil
	}
	r.wastedBytes+=int64(p.n)
	return false,nil
}
func(r *blockReader) launch(nextIndex int){
	if nextIndex<0{return}
	p:=&pendingRead{offset:int64(nextIndex)*blockSize,done:make(chan struct{})}
	r.pending=p
	dst:=r.ahead
	go func(){
		p.n,p.err=r.file.ReadAt(dst,p.offset)
		close(p.done)
	}()
}
func (r *blockReader) Read(off int64)([]byte,error){
	if off<0 || off%blockSize!=0 || off+blockSize>r.size{return nil,fmt.Errorf("unaligned/out-of-range offset %d",off)}
	switch r.mode {
	case "RESIDENT":return r.resident[int(off):int(off)+blockSize],nil
	case "MMAP":return r.mapped[int(off):int(off)+blockSize],nil
	case "SYNC":
		n,e:=r.file.ReadAt(r.current,off)
		r.readBytes+=int64(n)
		if e!=nil{return nil,e}
		if n!=blockSize{return nil,io.ErrUnexpectedEOF}
		return r.current,nil
	}
	hit,e:=r.settle(off,true);if e!=nil{return nil,e}
	if !hit {
		n,e:=r.file.ReadAt(r.current,off)
		r.readBytes+=int64(n)
		if e!=nil{return nil,e}
		if n!=blockSize{return nil,io.ErrUnexpectedEOF}
	}
	index:=int(off/blockSize)
	nBlocks:=int(r.size/blockSize)
	next:=-1
	if r.mode=="STATIC" {
		next=(index+1)%nBlocks
	} else {
		if r.seen>0 {
			delta:=(index-r.prevIndex+nBlocks)%nBlocks
			// No trace look-ahead: predict only after repeated observed deltas.
			if r.seen>=2 && delta==r.lastDelta {next=(index+delta)%nBlocks}
			r.lastDelta=delta
		}
	}
	r.seen++;r.prevIndex=index
	r.launch(next)
	return r.current,nil
}
func(r *blockReader)Close()error{
	_,e:=r.settle(-1,false)
	if r.mapped!=nil {if x:=unmapFile(r.mapped);e==nil{e=x}}
	return e
}

type workerResult struct {
	Schema string `json:"schema"`
	Mode string `json:"mode"`
	Schedule string `json:"schedule"`
	Seed uint64 `json:"seed"`
	SourceBytes int64 `json:"source_bytes"`
	RequestedBytes int64 `json:"requested_bytes"`
	UserReadBytes int64 `json:"user_read_bytes"`
	PrefetchedBytes int64 `json:"prefetched_bytes"`
	WastedPrefetchBytes int64 `json:"wasted_prefetch_bytes"`
	CacheHits int64 `json:"cache_hits"`
	TraceDigest string `json:"trace_digest"`
	ArithmeticChecksum string `json:"arithmetic_checksum"`
	PeakRSSBytes uint64 `json:"peak_rss_bytes"`
	MemoryMetric string `json:"memory_metric"`
	CacheClass string `json:"cache_class"`
}

func work(file,mode,schedule string,seed uint64)(out workerResult,err error){
	f,err:=os.Open(file);if err!=nil{return out,err}
	defer f.Close()
	info,err:=f.Stat();if err!=nil{return out,err}
	size:=info.Size()
	if size<2*blockSize || size%blockSize!=0{return out,fmt.Errorf("invalid source size %d",size)}
	sequence,err:=scheduleFor(schedule,int(size/blockSize),seed);if err!=nil{return out,err}
	r,err:=newBlockReader(f,mode,size);if err!=nil{return out,err}
	h:=sha256.New()
	checksum:=uint64(0xcbf29ce484222325)
	var requested int64
	for pass:=0;pass<2;pass++{
		for _,idx:=range sequence{
			b,e:=r.Read(int64(idx)*blockSize)
			if e!=nil{_ =r.Close();return out,e}
			if len(b)!=blockSize{_ =r.Close();return out,io.ErrUnexpectedEOF}
			_,_ =h.Write(b)
			for j:=0;j<blockSize;j+=8{
				checksum=bits.RotateLeft64(checksum^binary.LittleEndian.Uint64(b[j:j+8]),7)*0x100000001b3
			}
			requested+=blockSize
		}
	}
	if err=r.Close();err!=nil{return out,err}
	peak,e:=peakResidentBytes();if e!=nil{return out,e}
	if peak==0{return out,errors.New("unavailable peak physical RSS")}
	out=workerResult{
		Schema:schema,Mode:mode,Schedule:schedule,Seed:seed,
		SourceBytes:size,RequestedBytes:requested,UserReadBytes:r.readBytes,
		PrefetchedBytes:r.prefetchedBytes,WastedPrefetchBytes:r.wastedBytes,
		CacheHits:r.hits,TraceDigest:hex.EncodeToString(h.Sum(nil)),
		ArithmeticChecksum:fmt.Sprintf("%016x",checksum),PeakRSSBytes:peak,
		MemoryMetric:"OS_PROCESS_PEAK_PHYSICAL_RSS_BYTES",
		CacheClass:"WARM_OR_UNCONTROLLED_CACHE",
	}
	return out,nil
}
