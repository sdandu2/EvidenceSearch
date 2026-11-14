"use client";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { ArrowRight, ArrowUpRight, BookOpen, ChevronUp, Gauge, LoaderCircle, RotateCcw, Search as SearchIcon } from "lucide-react";
import { FormEvent, PointerEvent, useEffect, useRef, useState } from "react";
import { EvidenceDialog } from "@/components/ui/evidence-dialog";
import { RankComparison } from "@/components/rank-comparison";
import { ScienceScene } from "@/components/science-scene";
import { apiJson } from "@/lib/http";
import type { MethodKey, Paper, SearchResponse } from "@/lib/types";
import { METHOD_LABEL, METHODS } from "@/lib/types";

const examples = [
  {label:"Cell biology · Macrophages", query:"Bone marrow cells don't contribute to adult macrophage compartments."},
  {label:"Immunology · T cells", query:"TCR/CD3 microdomains are required to induce the immunologic synapse to activate T cells."},
  {label:"Genetics · Conservation", query:"Sequence conservation in gene regulatory regions between species is a poor predictor of conserved functionality."},
  {label:"Molecular biology · G-quadruplex", query:"Pyridostatin stabilizes the G - quadruplex in the telomeric region."},
  {label:"Cellular signaling · 4-PBA", query:"4-PBA treatment decreases endoplasmic reticulum stress in response to general endoplasmic reticulum stress markers."},
];

export function Discover() {
  const [query, setQuery] = useState("");
  const [result, setResult] = useState<SearchResponse | null>(null);
  const [method, setMethod] = useState<MethodKey>("reranked");
  const [isLoading,setLoading] = useState(false);
  const [error,setError] = useState("");
  const [inspect,setInspect] = useState<Paper | null>(null);
  const [compare,setCompare] = useState(false);
  const [status,setStatus] = useState<"checking"|"ready"|"offline">("checking");
  const reduceMotion=useReducedMotion();
  const inputRef=useRef<HTMLInputElement>(null);
  const searchCounter=useRef(0);
  useEffect(()=>{
    let active = true;
    const check = () => {
      apiJson<{status:string}>("/api/status")
        .then(data => { if(active) setStatus(data.status === "ready" ? "ready" : "offline"); })
        .catch(() => { if(active) setStatus("offline"); });
    };
    check();
    // Model initialization may finish after the web page loads.
    const ticker = window.setInterval(check, 12000);
    const onFocus = () => check();
    const keydown=(e:KeyboardEvent)=>{
      const inField = e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement || e.target instanceof HTMLSelectElement;
      if ((e.key==="/" && !inField) || ((e.ctrlKey || e.metaKey) && e.key.toLowerCase()==="k")) {
        e.preventDefault(); inputRef.current?.focus();
      }
    };
    window.addEventListener("keydown",keydown);
    window.addEventListener("focus",onFocus);
    return()=>{active=false;window.clearInterval(ticker);window.removeEventListener("focus",onFocus);window.removeEventListener("keydown",keydown);};
  },[]);

  async function submit(value:string) {
    const cleaned=value.trim();if(cleaned.length<3 || isLoading)return;
    const requestNumber=++searchCounter.current;
    setQuery(cleaned);setResult(null);setLoading(true);setError("");setCompare(false);
    try {
      const payload=await apiJson<SearchResponse>("/api/search",{
        method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify({query:cleaned})
      });
      if(requestNumber===searchCounter.current){setResult(payload);setMethod("reranked");setStatus("ready");}
    } catch(e) {if(requestNumber===searchCounter.current){setError(e instanceof Error?e.message:"Search failed");setStatus("offline");}}
    finally {if(requestNumber===searchCounter.current)setLoading(false);}
  }
  const resetSearch = () => {
    searchCounter.current += 1;
    setLoading(false); setResult(null); setQuery(""); setError("");
    setCompare(false); setInspect(null); setMethod("reranked");
    window.scrollTo({top:0,behavior:reduceMotion ? "auto" : "smooth"});
    window.requestAnimationFrame(()=>inputRef.current?.focus());
  };
  const onHeroPointerMove=(event: PointerEvent<HTMLElement>)=>{
    // Lightweight DOM-driven parallax: no React rerenders per pointer frame.
    if(event.pointerType === "touch" || reduceMotion) return;
    const rect=event.currentTarget.getBoundingClientRect();
    const x=(event.clientX-rect.left)/rect.width;
    const y=(event.clientY-rect.top)/rect.height;
    event.currentTarget.style.setProperty("--parallax-x",`${(x-.5)*24}px`);
    event.currentTarget.style.setProperty("--parallax-y",`${(y-.5)*18}px`);
    event.currentTarget.style.setProperty("--spot-x",`${(x*100).toFixed(2)}%`);
    event.currentTarget.style.setProperty("--spot-y",`${(y*100).toFixed(2)}%`);
  };
  const onHeroPointerLeave=(event: PointerEvent<HTMLElement>)=>{
    event.currentTarget.style.setProperty("--parallax-x","0px");
    event.currentTarget.style.setProperty("--parallax-y","0px");
    event.currentTarget.style.setProperty("--spot-x","75%");
    event.currentTarget.style.setProperty("--spot-y","45%");
  };
  const papers=result?.methods[method]||[];
  return <div className="discover-page">
    <motion.section className={`discovery-hero ${result?"hero-compact":""}`} onPointerMove={onHeroPointerMove} onPointerLeave={onHeroPointerLeave} layout transition={{duration:0.42}}>
      <div className="hero-copy"><span className="eyebrow"><span className="small-line"/> SCIENTIFIC DISCOVERY, ENGINEERED</span>
        <h1>Find the <em>evidence.</em></h1>
        <p>Ask a research question. Explore source abstracts. See how the evidence is ranked.</p>
      </div>
      <ScienceScene />
    </motion.section>
    <form className={`search-container ${result?"has-results":""}`} onSubmit={(e:FormEvent)=>{e.preventDefault();void submit(query);}}>
      <div className="search-main"><SearchIcon size={22} strokeWidth={1.6}/><input ref={inputRef} id="claim-search" autoComplete="off" value={query} onChange={e=>setQuery(e.target.value)} placeholder="Search a scientific question or claim..." maxLength={600} aria-label="Scientific claim or question"/>{result&&<button type="button" className="new-search-inline" onClick={resetSearch} aria-label="Start a new search"><RotateCcw size={16}/> New search</button>}<button className="submit-button" type="submit" disabled={isLoading||query.trim().length<3}>{isLoading?<LoaderCircle className="spin" size={19}/>:<>Explore evidence <ArrowRight size={18}/></>}</button></div>
      {!result&&<div className="search-metadata"><span><span className={`pulse-dot ${status==="offline"?"offline":""}`}/>{status==="checking"?"Connecting to local inference…":status==="ready"?"Local search engine ready":"Inference offline — start backend"}</span><span>SciFact · 5,183 indexed abstracts · not live web search</span></div>}
    </form>
    {!result&&<section className="example-dock" aria-label="Example research queries">
      <div className="example-dock-heading"><span className="eyebrow">NOT SURE WHERE TO START?</span><span>Use a curated claim, or write your own.</span></div>
      <div className="example-dock-control"><SearchIcon size={17}/><label htmlFor="example-query">Explore an example</label><select id="example-query" defaultValue="" disabled={isLoading} onChange={e=>{if(e.target.value){setQuery(e.target.value);inputRef.current?.focus();}}}><option value="" disabled>Choose a research topic…</option>{examples.map(x=><option key={x.label} value={x.query}>{x.label}</option>)}</select><ArrowRight size={16}/></div>
      <p className="fine-print">You can search freely within SciFact, but this collection is not the entire scientific literature.</p>
    </section>}
    {error&&<div role="alert" className="error-panel"><strong>Unable to complete search</strong><p>{error}</p><span>Check that the Python API is running on port 8000. Your query was not replaced with demo results.</span></div>}
    {isLoading&&<section className="loading-area" aria-live="polite"><span><LoaderCircle size={18} className="spin"/> Retrieving and reranking scientific abstracts...</span>{[1,2,3].map(i=><div key={i} className="skeleton-card"/>)}</section>}
    {result&&!isLoading&&<motion.section className="results" initial={reduceMotion?false:{opacity:0,y:30}} animate={{opacity:1,y:0}}>
      <div className="results-header"><div><span className="eyebrow">SCIFACT · SOURCE DOCUMENTS</span><h2>Evidence, ranked.</h2><p>Showing {papers.length} ranked abstracts from the indexed collection.</p></div><div className="results-stat"><Gauge size={17}/><strong>{(result.elapsed_ms/1000).toFixed(2)}s</strong><span>inference server</span></div></div>
      <div className="results-bar"><div className="segmented" role="group" aria-label="Retrieval method">{METHODS.map(k=><button key={k} className={method===k?"active":""} aria-pressed={method===k} onClick={()=>setMethod(k)}>{METHOD_LABEL[k]}</button>)}</div><button className="text-action" onClick={()=>setCompare(v=>!v)} aria-expanded={compare}><span>Compare ranking methods</span>{compare?<ChevronUp size={17}/>:<ArrowUpRight size={17}/>}</button></div>
      <AnimatePresence>{compare&&<RankComparison data={result} onClose={()=>setCompare(false)}/>}</AnimatePresence>
      <div className="papers"><AnimatePresence mode="wait"><motion.div key={`${result.query}-${method}`} initial={reduceMotion?false:{opacity:0,y:10}} animate={{opacity:1,y:0}} exit={reduceMotion?{}:{opacity:0,y:-8}} className="paper-list">{papers.map((p,i)=><motion.article key={p.document_id} className="paper-row" initial={reduceMotion?false:{opacity:0,y:15}} animate={{opacity:1,y:0}} transition={{delay:reduceMotion?0:Math.min(i*0.045,0.25)}}><div className="paper-index">{String(p.rank).padStart(2,"0")}</div><div className="paper-body"><div className="paper-metadata"><span>SCIFACT · {p.document_id}</span><span>RANK {p.rank}</span></div><h3>{p.title}</h3><p>{p.abstract}</p><button className="paper-link" onClick={()=>setInspect(p)}>Inspect full abstract <ArrowUpRight size={17}/></button></div></motion.article>)}</motion.div></AnimatePresence></div>
      <div className="results-foot"><BookOpen size={16}/><span>Ranked relevance is not scientific truth. Scores across different algorithms aren't comparable as probabilities.</span></div>
    </motion.section>}
    <EvidenceDialog paper={inspect} close={()=>setInspect(null)}/>
  </div>;
}
