"use client";
import { useEffect, useMemo, useRef, useState } from "react";
import { ArrowRight, BookOpen, Check, ChevronDown, ExternalLink, FlaskConical, Search, SlidersHorizontal, X } from "lucide-react";

type Domain = {name:string;documents:number;suggested_questions:string[]};
type Paper = {paper_id:string;rank:number;title:string;abstract:string;year:number|string;authors:string|string[];venue:string;doi:string;source_url:string;score:number};
type Method = "reranked"|"hybrid"|"dense"|"bm25"|"tfidf";
type SearchResult = {query:string;domain:string;filtered_count:number;elapsed_ms:number;methods:Record<Method,Paper[]>;evaluation:string;score_note:string;public_abstract_rights:string};
const FIELDS = ["Neuroscience","Climate Science","Quantum Computing","Genetics","Immunology"];
const METHOD_LABEL:Record<Method,string> = {reranked:"Cross-encoder",hybrid:"Hybrid",dense:"Semantic",bm25:"Keyword",tfidf:"TF-IDF"};
const FALLBACK:Record<string,string> = {
  "Neuroscience":"How does sleep influence memory consolidation?",
  "Climate Science":"What evidence connects ocean warming to coral bleaching?",
  "Quantum Computing":"What limits superconducting qubit coherence?",
  "Genetics":"How do noncoding variants influence disease risk?",
  "Immunology":"How do T cells recognize antigens?"
};
function isSourceUrl(value:string):boolean { try {const u=new URL(value); return u.protocol==="http:"||u.protocol==="https:";}catch{return false;} }
export function ResearchExplorer(){
  const [domains,setDomains]=useState<Domain[]>([]);
  const [domain,setDomain]=useState(FIELDS[0]);
  const [query,setQuery]=useState("");
  const [year,setYear]=useState("any");
  const [method,setMethod]=useState<Method>("reranked");
  const [result,setResult]=useState<SearchResult|null>(null);
  const [selected,setSelected]=useState<string|null>(null);
  const [loading,setLoading]=useState(false);
  const [error,setError]=useState("");
  const [showAbstract,setShowAbstract]=useState(true);
  const sectionRef=useRef<HTMLElement|null>(null);
  useEffect(()=>{let active=true;fetch("/api/research/domains",{cache:"no-store"}).then(async r=>{if(!r.ok)throw new Error("Backend unavailable");return r.json();}).then(d=>{if(active)setDomains(d.fields||[]);}).catch(()=>{if(active)setError("Start the FastAPI backend to load indexed collections.");});return()=>{active=false;};},[]);
  const choices=domains.find(d=>d.name===domain)?.suggested_questions||[FALLBACK[domain]];
  const shown=result?.methods?.[method]||[];
  const activePaper=useMemo(()=>shown.find(p=>p.paper_id===selected),[shown,selected]);
  function changeDomain(value:string){setDomain(value);setQuery("");setResult(null);setSelected(null);setError("");}
  async function search(question?:string){
    const q=(question??query).trim();if(q.length<3){setError("Enter a question or choose an example.");return;}
    setLoading(true);setError("");setSelected(null);setQuery(q);
    try{
      const resp=await fetch("/api/research/search",{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify({query:q,domain,year_min:year==="any"?null:Number(year)})});
      const data=await resp.json();if(!resp.ok)throw new Error(data.detail||"Search failed");
      setResult(data as SearchResult);setMethod("reranked");
      requestAnimationFrame(()=>sectionRef.current?.scrollIntoView({behavior:"smooth",block:"start"}));
    }catch(e){setError(e instanceof Error?e.message:"Search could not be completed");}
    finally{setLoading(false);}
  }
  return <div className="research-app">
    <header className="research-top"><a className="research-logo" href="/"><span className="research-monogram"><FlaskConical size={20}/></span><span>Evidence<span className="research-accent">Search</span></span></a><div className="research-top-links"><a href="/performance">SciFact benchmark</a><a href="/methodology">Methodology</a><span className="research-live-indicator">Local research preview</span></div></header>
    <main>
      <section className="research-hero">
        <div className="research-kicker"><span className="research-kicker-line"/> SCIENTIFIC LITERATURE DISCOVERY</div>
        <div className="research-hero-grid"><div><h1>Better questions.<br/><em>Better evidence.</em></h1><p>Explore real research abstracts across five disciplines. Compare retrieval methods and inspect the original source behind every result.</p></div><div className="research-illustration" aria-hidden="true"><div className="research-orbit orbit-1"/><div className="research-orbit orbit-2"/><div className="research-orbit orbit-3"/><span className="research-core"/><span className="research-star s1"/><span className="research-star s2"/><span className="research-star s3"/></div></div>
      </section>
      <section className="research-panel" aria-label="Search literature">
        <div className="research-panel-header"><h2>Start your research</h2><span>Five indexed scientific collections</span></div>
        <div className="research-fields" role="group" aria-label="Research field">
          {FIELDS.map((f,i)=><button key={f} className={domain===f?"research-field active":"research-field"} type="button" onClick={()=>changeDomain(f)} aria-pressed={domain===f}><span className="field-index">0{i+1}</span>{f}<span className="field-dot"/></button>)}
        </div>
        <div className="research-form">
          <label className="research-label" htmlFor="question">Your research question</label>
          <div className="research-query"><Search size={22}/><input id="question" value={query} onChange={e=>setQuery(e.target.value)} onKeyDown={e=>{if(e.key==="Enter")void search();}} placeholder="Ask a scientific question..." maxLength={600}/><button disabled={loading} type="button" onClick={()=>void search()}>{loading?"Searching...":"Explore evidence"}<ArrowRight size={17}/></button></div>
          <div className="research-under-query"><div className="research-select-wrap"><label htmlFor="prompt">Or try a guided question</label><div className="research-select-shell"><select id="prompt" value={choices.includes(query) ? query : ""} onChange={e=>setQuery(e.target.value)}><option value="" disabled>Choose an example</option>{choices.map((q,i)=><option key={`${q}-${i}`} value={q}>{q}</option>)}</select><ChevronDown size={16}/></div></div><div className="research-select-wrap year-select"><label htmlFor="year">Published since</label><div className="research-select-shell"><select id="year" value={year} onChange={e=>setYear(e.target.value)}><option value="any">Any year</option>{[2026,2024,2020,2015,2010].map(y=><option value={y} key={y}>{y}</option>)}</select><ChevronDown size={16}/></div></div></div>
          <div className="research-panel-foot"><span><BookOpen size={15}/> {domains.find(d=>d.name===domain)?.documents?.toLocaleString()??"—"} indexed papers in {domain}</span><span>Frozen local corpus · Not live web search</span></div>
          {error&&<p className="research-error" role="alert">{error}</p>}
        </div>
      </section>
      {result&&<section ref={sectionRef} className="research-results" aria-label="Search results">
        <div className="research-results-heading"><div><span className="research-kicker">RETRIEVAL RESULTS</span><h2>Findings for your question</h2><p>Searching {result.filtered_count.toLocaleString()} eligible papers in {result.domain}. <span>Measured server time: {(result.elapsed_ms/1000).toFixed(2)} s.</span></p></div><button className="research-reset" onClick={()=>{setResult(null);setSelected(null);window.scrollTo({top:0,behavior:"smooth"});}}>New search <X size={16}/></button></div>
        <div className="research-results-controls"><div className="research-methods" role="group" aria-label="Retrieval method">{(["reranked","hybrid","dense","bm25","tfidf"] as Method[]).map(m=><button key={m} onClick={()=>{setMethod(m);setSelected(null);}} className={method===m?"active":""} aria-pressed={method===m}>{METHOD_LABEL[m]}</button>)}</div><span className="research-count">Top {shown.length} / {result.filtered_count}</span></div>
        <div className="research-results-columns"><div className="research-result-list">{shown.length?shown.map(p=><button key={p.paper_id} className={selected===p.paper_id?"research-result-card selected":"research-result-card"} onClick={()=>setSelected(p.paper_id)}><div className="result-line"><span>#{String(p.rank).padStart(2,"0")}</span><span>{p.year||"Year unknown"} · {METHOD_LABEL[method]}</span></div><h3>{p.title}</h3><p>{(p.abstract||"").slice(0,260)}{(p.abstract||"").length>260?"…":""}</p><span className="result-open">Inspect source <ArrowRight size={15}/></span></button>):<div className="research-empty">No indexed papers match these filters. Try another period or question.</div>}</div><aside className="research-reader"><div className="research-reader-kicker">SOURCE INSPECTION <BookOpen size={16}/></div>{activePaper?<><h3>{activePaper.title}</h3><div className="research-reader-metadata"><span>{activePaper.year||"Year unknown"}</span><span>{Array.isArray(activePaper.authors)?activePaper.authors.slice(0,4).join(", "):String(activePaper.authors||"").slice(0,180)}</span>{activePaper.venue&&<span>{activePaper.venue}</span>}</div><button type="button" className="research-abstract-toggle" onClick={()=>setShowAbstract(!showAbstract)}>Original abstract <ChevronDown size={16}/></button>{showAbstract&&<p className="research-abstract">{activePaper.abstract}</p>}<div className="research-source-details">Document ID: {activePaper.paper_id}{activePaper.doi&&<> · DOI: {activePaper.doi}</>}</div>{isSourceUrl(activePaper.source_url)&&<a href={activePaper.source_url} target="_blank" rel="noreferrer" className="research-source-link">Open publication source <ExternalLink size={16}/></a>}</>:<div className="research-reader-empty"><SlidersHorizontal size={26}/><p>Select a paper to inspect its source abstract and publication metadata.</p></div>}</aside></div>
        <div className="research-disclaimer"><Check size={16}/><span>These rankings reflect document relevance, not scientific truth. Labels on the expanded collection are provisional; abstract reuse rights have not been verified for public redistribution.</span></div>
      </section>}
    </main>
    <footer className="research-footer"><span>EvidenceSearch · Local scientific discovery preview</span><span>Real papers · Traceable sources · No fabricated citations</span></footer>
  </div>;
}
