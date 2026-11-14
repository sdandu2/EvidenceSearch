"use client";

import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { ArrowDown, ArrowLeft, ArrowRight, ArrowUpRight, BookOpenText, Check, ChevronDown, Compass, Layers3, LoaderCircle, RotateCcw, ScanEye, Sparkles, X } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { apiJson } from "@/lib/http";
import type { BenchmarkData, MethodKey, Paper, SearchResponse } from "@/lib/types";
import { METHOD_LABEL } from "@/lib/types";
import { WorldCanvas } from "./world-canvas";
import { WORLDS, type World, type WorldKey } from "./worlds";

interface AtlasPoint { document_id:string; title:string; abstract:string; x:number; y:number; query_cosine:number; ranks:Record<MethodKey,number|null>; }
interface AtlasLink {source:string;target:string;cosine:number}
interface AtlasResponse {points:AtlasPoint[];links:AtlasLink[];layout:string;note:string;}
type ObservatoryResponse=SearchResponse & {atlas?:AtlasResponse};
type View = "explore" | "performance" | "methodology";
const models:Array<{key:MethodKey; label:string}> = [
  {key:"reranked",label:"Intelligent"}, {key:"hybrid",label:"Combined"},{key:"bm25",label:"Keyword"}
];
function WorldGlyph({kind,color}:{kind:WorldKey;color:string}) {
  const root={className:"obs-world-glyph",viewBox:"0 0 48 48",fill:"none",stroke:"currentColor",style:{color},strokeWidth:1.35,strokeLinecap:"round" as const,strokeLinejoin:"round" as const,"aria-hidden":true as const};
  if(kind==="neural")return <svg {...root}><path d="M23 23 9 10M23 23 38 9M23 23 39 36M23 23 9 37M23 23 20 8M23 23 26 41"/><circle cx="23" cy="23" r="5"/><circle cx="9" cy="10" r="2.5"/><circle cx="38" cy="9" r="2.5"/><circle cx="39" cy="36" r="2.5"/><circle cx="9" cy="37" r="2.5"/></svg>;
  if(kind==="climate")return <svg {...root}><circle cx="24" cy="24" r="16"/><ellipse cx="24" cy="24" rx="7" ry="16"/><path d="M9 24h30M13 15c7 5 15 5 22 0M13 33c7-5 15-5 22 0"/></svg>;
  if(kind==="quantum")return <svg {...root}><path d="M7 24c8-16 11 16 19 0s12-16 16 0M7 31c9-15 13 12 20-1s10-8 15 1"/><circle cx="24" cy="12" r="2.8"/><path d="M24 8v-4M24 16v3"/></svg>;
  if(kind==="genetics")return <svg {...root}><path d="M13 5c19 12 3 26 22 38M35 5c-19 12-3 26-22 38M14 10h20M19 17h10M19 31h10M14 38h20"/></svg>;
  return <svg {...root}><circle cx="24" cy="24" r="12"/><circle cx="24" cy="24" r="5"/><path d="M24 8v-5M24 45v-5M8 24H3M45 24h-5M12 12l-4-4M36 36l4 4M36 12l4-4M12 36l-4 4"/><circle cx="9" cy="24" r="2"/><circle cx="39" cy="24" r="2"/></svg>;
}
function EmptyIcon({size=18}:{size?:number}){return <span style={{display:"inline-block",width:size,height:size,border:"1px solid currentColor",borderRadius:"50%"}}/>;}
function getWorld(key:WorldKey):World {return WORLDS.find(w=>w.key===key)||WORLDS[0];}
function percent(value:number){return (value*100).toFixed(2)+"%";}
type AtlasLayout={centerX:number;centerY:number;scale:number};
// Fit the observed 2D embedding sample into the viewport WITHOUT stretching its axes.
// This is a visual display transform, not a new model projection or new measurement.
function fitAtlas(points:AtlasPoint[]):AtlasLayout {
  if(!points.length)return {centerX:0,centerY:0,scale:330};
  const xs=points.map(p=>p.x),ys=points.map(p=>p.y);
  const minX=Math.min(...xs),maxX=Math.max(...xs),minY=Math.min(...ys),maxY=Math.max(...ys);
  const rangeX=Math.max(maxX-minX,.15),rangeY=Math.max(maxY-minY,.15);
  return {centerX:(maxX+minX)/2,centerY:(maxY+minY)/2,scale:Math.min(700/rangeX,400/rangeY,3500)};
}
function toPoint(p:AtlasPoint,method:MethodKey,mode:"semantic"|"rank",fit:AtlasLayout) {
  if(mode==="semantic")return {x:450+(p.x-fit.centerX)*fit.scale,y:280+(p.y-fit.centerY)*fit.scale};
  const rank=p.ranks[method]??105;
  const radius=55+Math.min(rank,100)/100*188;
  const angle=Math.atan2(p.y-fit.centerY+.008,p.x-fit.centerX+.013);
  return {x:450+Math.cos(angle)*radius*1.30,y:280+Math.sin(angle)*radius*.95};
}
function Atlas({data,world,method,onMethodChange,onInspect}:{data:ObservatoryResponse;world:World;method:MethodKey;onMethodChange:(v:MethodKey)=>void;onInspect:(paper:Pick<Paper,"document_id"|"title"|"abstract">)=>void}){
  const atlas=data.atlas;
  const [mode,setMode]=useState<"semantic"|"rank">("semantic");
  const [focused,setFocused]=useState("");
  const [hover,setHover]=useState("");
  const reduced=useReducedMotion();
  const points=atlas?.points||[];
  const activeId=focused||data.methods[method][0]?.document_id||points[0]?.document_id||"";
  const selected=points.find(p=>p.document_id===activeId);
  const byId=useMemo(()=>new Map(points.map(p=>[p.document_id,p])),[points]);
  const fit=useMemo(()=>fitAtlas(points),[points]);
  const mapRef=useRef<SVGSVGElement>(null);
  const selectedPaper=selected ? {document_id:selected.document_id,title:selected.title,abstract:selected.abstract} : null;
  const methodRank=(p:AtlasPoint)=>p.ranks[method];
  const rankText=(rank:number|null|undefined)=>rank==null?"Not in top 100":`#${rank}`;
  return <section className="obs-atlas-section" aria-label="Interactive map of retrieved documents">
    <div className="obs-section-heading">
      <div><span className="obs-kicker">02 / THE LITERATURE ATLAS</span><h2>Find the signal<br/><em>in the literature.</em></h2><p>Real SciFact documents. One question. Different ways of seeing relevance.</p></div>
      <span className="obs-micro-stat">{points.length} mapped documents <span aria-hidden="true">·</span> {Math.round(data.elapsed_ms)} ms inference</span>
    </div>
    <div className="obs-atlas-shell">
      <div className="obs-atlas-top">
        <div className="obs-lens-head"><span className="obs-overline">CHANGE THE LENS</span><span className="obs-lens-sub">See how each model orders the same documents</span></div>
        <div className="obs-lens-tabs" role="group" aria-label="Ranking model">{models.map(m=><button key={m.key} onClick={()=>{onMethodChange(m.key);setFocused("");}} aria-pressed={m.key===method} className={method===m.key?"active":""}>{m.label}</button>)}</div>
      </div>
      <div className="obs-atlas-toolrow"><div className="obs-display-tabs" role="group" aria-label="Atlas layout"><button aria-pressed={mode==="semantic"} className={mode==="semantic"?"selected":""} onClick={()=>setMode("semantic")}>Spatial map</button><button aria-pressed={mode==="rank"} className={mode==="rank"?"selected":""} onClick={()=>setMode("rank")}>Rank orbits</button></div><div className="obs-map-hint"><span className="obs-key-light"/> Select a point to inspect its source</div></div>
      <div className="obs-atlas-body">
        <div className="obs-map-area">
          <div className="obs-atlas-world-backdrop" aria-hidden="true"><WorldCanvas world={world.key} variant="atlas" compact/></div>
          <svg ref={mapRef} className="obs-atlas-svg" viewBox="0 0 900 560" onPointerMove={e=>{if(reduced||!mapRef.current)return;const box=e.currentTarget.getBoundingClientRect();const nx=(e.clientX-box.left)/box.width-.5;const ny=(e.clientY-box.top)/box.height-.5;mapRef.current.style.transform=`perspective(1300px) rotateY(${(nx*3).toFixed(2)}deg) rotateX(${(-ny*3).toFixed(2)}deg)`;}} onPointerLeave={()=>{if(mapRef.current)mapRef.current.style.transform="";}} role="img" aria-label={`${mode==="semantic"?"Approximate 2D embedding layout":"Radial positions according to ranking"} of returned SciFact documents for ${data.query}`}>
            <defs>
              <radialGradient id="atlas-soft" cx="50%" cy="50%" r="52%"><stop offset="0%" stopColor={world.accent} stopOpacity=".10"/><stop offset="100%" stopColor={world.accent} stopOpacity="0"/></radialGradient>
              <filter id="atlas-glow"><feGaussianBlur stdDeviation="7"/></filter>
            </defs>
            <rect width="900" height="560" fill="url(#atlas-soft)"/>
            {[100,190,275].map(r=><ellipse key={r} cx="450" cy="280" rx={r*1.25} ry={r*.76} fill="none" stroke="#7592a7" strokeWidth="1" opacity=".07" strokeDasharray="3 11"/>)}
            <line x1="450" y1="36" x2="450" y2="526" stroke="#63849a" opacity=".08"/>
            <line x1="42" y1="280" x2="858" y2="280" stroke="#63849a" opacity=".08"/>
            {(atlas?.links||[]).slice(0,55).map((link,i)=>{
              const a=byId.get(link.source),b=byId.get(link.target);if(!a||!b)return null;
              const pa=toPoint(a,method,mode,fit),pb=toPoint(b,method,mode,fit);
              return <motion.line key={`${link.source}-${link.target}`} animate={{x1:pa.x,y1:pa.y,x2:pb.x,y2:pb.y,opacity:(activeId===a.document_id||activeId===b.document_id) ? .49 : .085}} transition={{duration:reduced?0:.72}} stroke="#98BED1" strokeWidth={1} strokeDasharray="3 7"/>;
            })}
            {points.map((p,i)=>{
              const pos=toPoint(p,method,mode,fit);
              const isSelected=activeId===p.document_id;
              const isHover=hover===p.document_id;
              const rank=methodRank(p);
              const radius=isSelected?7.5:(rank!=null&&rank<=10?4.6:3.2);
              return <motion.g key={p.document_id} animate={{x:pos.x,y:pos.y,opacity:rank==null?.32:1}} transition={{type:"spring",stiffness:65,damping:17,duration:reduced?0:undefined}}>
                {(isSelected||isHover)&&<circle cx="0" cy="0" r="20" fill={world.accent} opacity=".14" filter="url(#atlas-glow)"/>}
                <circle cx="0" cy="0" r={radius+9} fill={world.accent} opacity={isSelected?.14:0}/>
                <circle cx="0" cy="0" r={radius} fill={isSelected?"#E3FFF9":rank!=null&&rank<=10?world.accent:"#607B92"} stroke={isSelected?world.accent:"#0B121A"} strokeWidth={isSelected?2:1.2}/>
                {(isSelected||isHover)&&<text x="12" y="-11" className="obs-map-label">{(p.title||p.document_id).slice(0,28)}{p.title.length>28?"…":""}</text>}
                <circle r="17" fill="transparent" onClick={()=>setFocused(p.document_id)} onMouseEnter={()=>setHover(p.document_id)} onMouseLeave={()=>setHover("")} style={{cursor:"pointer"}}/>
              </motion.g>;
            })}

          </svg>
          <p className="obs-map-provenance">{mode==="semantic"?"2D MiniLM embedding projection, uniformly scaled to fit the visible papers. Links indicate embedding similarity—not citations, agreement or scientific truth.":"Orbit radius encodes rank under the selected model; nearer the center means higher rank. Angle has no scientific meaning."}</p>
        </div>
        <div className="obs-map-aside">
          <span className="obs-overline">DOCUMENT INSPECTOR</span>
          <label className="obs-paper-select-label" htmlFor="obs-paper-select">Follow a document</label>
          <select id="obs-paper-select" value={activeId} onChange={e=>setFocused(e.target.value)} className="obs-paper-select">{points.map(p=><option key={p.document_id} value={p.document_id}>{p.title} · {p.document_id}</option>)}</select>
          {selected&&<AnimatePresence mode="wait"><motion.div key={selected.document_id} initial={reduced?false:{opacity:0,y:14}} animate={{opacity:1,y:0}} exit={reduced?undefined:{opacity:0,y:-8}}>
            <h3 className="obs-selected-title">{selected.title}</h3>
            <span className="obs-source-tag">SCIFACT / {selected.document_id}</span>
            <div className="obs-rank-triplet">{(["bm25","hybrid","reranked"] as MethodKey[]).map(key=><div key={key}><span>{key==="bm25"?"Keyword":key==="hybrid"?"Combined":"Intelligent"}</span><strong>{rankText(selected.ranks[key])}</strong></div>)}</div>
            <p className="obs-aside-copy">The selected document's rank changes across algorithms. Rank is a measure of search ordering—not scientific truth.</p>
            {selectedPaper?<button className="obs-text-button" onClick={()=>onInspect(selectedPaper)}>Read original abstract <ArrowUpRight size={16}/></button>:<p className="obs-aside-copy">This document appears in the candidate pool but is outside the visible top results.</p>}
          </motion.div></AnimatePresence>}
          <div className="obs-atlas-bottom-note">This view contains <strong>real retrieved documents</strong>. The 2D layout is a visualization of model embeddings and is not a map of citations or verified scientific relationships.</div>
        </div>
      </div>
    </div>
  </section>;
}

function Reader({paper,onClose}:{paper:Pick<Paper,"document_id"|"title"|"abstract">;onClose:()=>void}){
  const closeRef=useRef<HTMLButtonElement>(null);
  useEffect(()=>{closeRef.current?.focus();const k=(e:KeyboardEvent)=>{if(e.key==="Escape")onClose();};window.addEventListener("keydown",k);const prev=document.body.style.overflow;document.body.style.overflow="hidden";return()=>{document.body.style.overflow=prev;window.removeEventListener("keydown",k);};},[onClose]);
  return <div className="obs-reader-backdrop" onMouseDown={e=>{if(e.target===e.currentTarget)onClose();}}>
    <motion.section role="dialog" aria-modal="true" aria-label={`Read ${paper.title}`} className="obs-reader" initial={{opacity:0,x:60}} animate={{opacity:1,x:0}} exit={{opacity:0,x:60}}>
      <div className="obs-reader-top"><span>SCIFACT / DOCUMENT {paper.document_id}</span><button ref={closeRef} className="obs-icon-button" aria-label="Close abstract" onClick={onClose}><X size={21}/></button></div>
      <div className="obs-reader-content"><span className="obs-kicker">SOURCE MATERIAL / UNEDITED ABSTRACT</span><h2>{paper.title}</h2><p>{paper.abstract}</p><div className="obs-reader-footer"><BookOpenText size={18}/><span>Original SciFact abstract, retrieved from the local corpus. The search model ranks relevance; it does not verify this claim.</span></div></div>
    </motion.section>
  </div>;
}

function Performance({world}:{world:World}) {
  const [data,setData]=useState<BenchmarkData|null>(null);
  const [error,setError]=useState("");
  const [metric,setMetric]=useState<"Recall@10"|"nDCG@10"|"MRR@10">("Recall@10");
  const explanations={
    "Recall@10":{name:"Coverage of relevant evidence",question:"Out of the papers known to be relevant, what share appeared within the first 10 results?",example:"If a question has 5 judged-relevant papers and 4 appear in the top 10, recall is 80% for that question.",note:"Average per-query recall across the 647-query holdout. Unjudged documents are not necessarily irrelevant."},
    "nDCG@10":{name:"Quality of the ordering",question:"Are the most relevant results positioned near the top of the first 10?",example:"A relevant paper at position 1 contributes more than the same paper at position 9.",note:"Normalized discounted cumulative gain, scaled between 0 and 1 (higher is better)."},
    "MRR@10":{name:"Speed to the first relevant result",question:"How early does the first judged-relevant result appear?",example:"A first relevant paper at rank 1 scores 1.0; at rank 2 it scores 0.5.",note:"Mean reciprocal rank of the first judged-relevant result in the top 10."}
  };
  useEffect(()=>{apiJson<BenchmarkData>("/api/benchmarks").then(setData).catch(e=>setError(e instanceof Error?e.message:"Benchmarks unavailable"));},[]);
  const selected=data?.metrics["CE · RRF@100"]?.[metric]??0;
  const base=data?.metrics["BM25"]?.[metric]??0;
  return <section className="obs-inner-page">
    <div className="obs-overline">THE EVIDENCE / VERIFIED RESULTS</div>
    <div className="obs-wide-heading"><h1>Beautiful ideas.<br/><em>Measured results.</em></h1><p>Behind the visuals, there is a real retrieval system. Here is what it accomplished on 647 reserved SciFact queries.</p></div>
    <div className="obs-proof-grid"><div className="obs-proof-art"><WorldCanvas world={world.key} variant="performance"/><div className="obs-proof-mark">NOT A DEMO METRIC<br/>RESULTS FROM NOTEBOOK 05</div></div><div className="obs-proof-copy"><span className="obs-kicker">WHY IT MATTERS</span><h2>More of the right papers.<br/>Closer to the top.</h2><p>We compare traditional keyword search against a hybrid retrieval system with neural reranking. Both search the exact same documents.</p></div></div>
    {error&&<div className="obs-error" role="alert">Live benchmark report unavailable: {error}. Start the FastAPI service; no fictional scores will be displayed.</div>}
    {!data&&!error&&<p className="obs-loading">Retrieving the verified evaluation report…</p>}
    {data&&<div className="obs-performance-content"><div className="obs-metric-control" role="group" aria-label="Performance question"><button aria-pressed={metric==="Recall@10"} onClick={()=>setMetric("Recall@10")}>Evidence found</button><button aria-pressed={metric==="nDCG@10"} onClick={()=>setMetric("nDCG@10")}>Result ordering</button><button aria-pressed={metric==="MRR@10"} onClick={()=>setMetric("MRR@10")}>First relevant paper</button></div><div className="obs-metric-story"><div><span className="obs-overline">{metric} / RESERVED INTERNAL HOLDOUT</span><motion.h2 key={metric} initial={{opacity:0,y:10}} animate={{opacity:1,y:0}}>{metric==="Recall@10"?percent(selected):selected.toFixed(4)}</motion.h2><h3 className="obs-metric-explainer-title">{explanations[metric].name}</h3><p>{explanations[metric].question}</p><span className="obs-change">+{metric==="Recall@10"?((selected-base)*100).toFixed(2)+" percentage points":(selected-base).toFixed(4)} vs. keyword search</span></div><div className="obs-meter-comparison">{(["BM25","Hybrid RRF","CE · RRF@100"] as const).map(k=>{const v=data.metrics[k][metric];return <div className="obs-meter" key={k}><div><span>{k==="BM25"?"Keyword":k==="Hybrid RRF"?"Combined":"EvidenceSearch"}</span><strong>{metric==="Recall@10"?percent(v):v.toFixed(4)}</strong></div><div className="obs-meter-track"><motion.div animate={{width:`${Math.max(0,Math.min(1,v))*100}%`}} transition={{duration:.6}}/></div></div>})}<span className="obs-data-caption">Bars start at zero. Results represent relevance judgments, not the probability that a claim is true.</span></div></div><div className="obs-metric-definition"><div><span className="obs-overline">EXAMPLE</span><p>{explanations[metric].example}</p></div><div><span className="obs-overline">WHAT THIS MEASURES</span><p>{explanations[metric].note}</p></div></div><p className="obs-method-foot">Measured on a reserved internal set of 647 SciFact training queries. The original test set had been inspected in earlier experiments. This evaluation does not imply performance on all scientific fields.</p></div>}
  </section>;
}
function Methodology({world}:{world:World}) {
  const stages=[
    {title:"Retrieve",label:"01",desc:"Cast a wide net using two independent search strategies.",detail:"Two retrievers each return 100 candidates.",how:"BM25 searches for exact words and technical terms, while a pretrained MiniLM encoder compares the question with scientific abstracts in embedding space. Both search the same 5,183-document SciFact collection.",why:"Scientific questions mix exact terminology with paraphrases. Running lexical and semantic searches independently helps catch documents either method may overlook.",next:"Two ranked lists of up to 100 real document IDs, plus their model-specific scores."},
    {title:"Fuse",label:"02",desc:"Combine the complementary candidate lists without comparing incompatible scores.",detail:"Reciprocal Rank Fusion · fixed constant k = 60.",how:"Reciprocal Rank Fusion rewards papers that rank highly in either list. We use each paper’s position—not its raw BM25 or MiniLM similarity score—and keep the fused top 100.",why:"Lexical matching and embedding similarity use different score scales; adding those scores directly would be misleading. Rank fusion combines them in a reproducible way.",next:"One shortlist of 100 candidates, ready for more careful relevance assessment."},
    {title:"Rerank",label:"03",desc:"Evaluate each shortlisted abstract against the question as a pair.",detail:"MS MARCO MiniLM-L6 cross-encoder · 100 pairs.",how:"The cross-encoder receives the complete query and each candidate abstract together. Unlike independent embeddings, it can examine the interaction between the query words and the abstract before assigning a ranking score.",why:"The initial retrievers prioritize coverage. A slower pairwise model spends its compute only on the small shortlist, improving the order shown to the reader.",next:"A ranked result set with document IDs and scores. Scores indicate retrieval order, not calibrated truth probabilities."},
    {title:"Inspect",label:"04",desc:"Put traceable source material in front of the reader.",detail:"Original title, abstract and SciFact document ID.",how:"The application fetches and displays the original indexed title and abstract, with a stable document identifier. The user can compare how its position differs across Keyword, Combined and Intelligent views.",why:"A search system should let people read the evidence for themselves. We do not generate paper titles, substitute abstracts or convert high relevance into a scientific verdict.",next:"A readable research starting point—not a fact check, citation graph, or live-web search."},
  ];
  const [stage,setStage]=useState(0);
  const reduced=useReducedMotion();
  const selected=stages[stage];
  return <section className="obs-inner-page obs-methodology-page">
    <span className="obs-overline">BEHIND THE INSTRUMENT</span>
    <div className="obs-wide-heading"><h1>The science<br/><em>of finding science.</em></h1><p>Four transparent steps transform a scientific question into ranked, inspectable source documents. Select a stage to see how it works and what it contributes.</p></div>
    <div className="obs-method-grid"><div className="obs-method-art"><WorldCanvas world={world.key} variant="methodology" stage={stage}/><div className="obs-method-orbit"><span className="obs-kicker">{selected.label} / 04</span><strong>{selected.title}</strong><p>{selected.detail}</p></div></div>
      <div className="obs-method-stepper">{stages.map((s,i)=><button key={s.label} onClick={()=>setStage(i)} className={`obs-method-step ${stage===i?"active":""}`} aria-pressed={stage===i}><span>{s.label}</span><div><strong>{s.title}</strong><p>{s.desc}</p></div><ArrowUpRight size={17}/></button>)}</div></div>
    <AnimatePresence mode="wait"><motion.div key={selected.label} initial={reduced?false:{opacity:0,y:12}} animate={{opacity:1,y:0}} exit={reduced?undefined:{opacity:0,y:-8}} className="obs-method-deep-dive">
      <div className="obs-deep-dive-heading"><span className="obs-overline">INSIDE STEP {selected.label}</span><h2>{selected.title}: the reasoning behind the system.</h2></div>
      <div className="obs-deep-dive-columns"><div><span className="obs-deep-label">HOW IT WORKS</span><p>{selected.how}</p></div><div><span className="obs-deep-label">WHY WE DO IT</span><p>{selected.why}</p></div><div><span className="obs-deep-label">WHAT COMES NEXT</span><p>{selected.next}</p></div></div>
    </motion.div></AnimatePresence>
    <div className="obs-trust-strip"><div><strong>5,183</strong><span>Indexed SciFact abstracts</span></div><div><strong>647</strong><span>Reserved internal evaluation queries</span></div><div><strong>3</strong><span>Compared retrieval methods</span></div></div>
    <p className="obs-method-foot">EvidenceSearch ranks scientific abstracts. It does not determine whether a scientific statement is true, supported or refuted; SciFact relevance labels are not exhaustive. The initial dataset is not the live scholarly web, and results outside its coverage may be weak.</p>
  </section>;
}

export function Observatory() {
  const [worldKey,setWorldKey]=useState<WorldKey>("immune");
  const [view,setView]=useState<View>("explore");
  const [response,setResponse]=useState<ObservatoryResponse|null>(null);
  const [loading,setLoading]=useState(false);
  const [error,setError]=useState("");
  const [ready,setReady]=useState<"checking"|"ready"|"offline">("checking");
  const [method,setMethod]=useState<MethodKey>("reranked");
  const [reader,setReader]=useState<Pick<Paper,"document_id"|"title"|"abstract">|null>(null);
  const [customMode,setCustomMode]=useState(false);
  const [customQuery,setCustomQuery]=useState("");
  const cancel=useRef(0);
  const lessMotion=useReducedMotion();
  const world=getWorld(worldKey);
  const currentQuery=customMode?customQuery:world.query;
  const goTo=(next:View)=>{setView(next);window.scrollTo({top:0,behavior:lessMotion?"auto":"smooth"});};
  const reset=()=>{cancel.current++;setLoading(false);setResponse(null);setError("");setReader(null);window.scrollTo({top:0,behavior:lessMotion?"auto":"smooth"});};
  useEffect(()=>{
    let active=true;const ping=()=>apiJson<{status:string}>("/api/status").then(v=>{if(active)setReady(v.status==="ready"?"ready":"offline");}).catch(()=>{if(active)setReady("offline");});ping();const id=window.setInterval(ping,15000);return()=>{active=false;clearInterval(id);};
  },[]);
  const run=useCallback(async()=>{
    const q=currentQuery.trim();if(q.length<3||loading)return;
    const runId=++cancel.current;setLoading(true);setError("");setResponse(null);setMethod("reranked");
    try{
      const data=await apiJson<ObservatoryResponse>("/api/search",{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify({query:q})});
      if(runId===cancel.current){setResponse(data);setReady("ready");requestAnimationFrame(()=>requestAnimationFrame(()=>document.querySelector(".obs-query-band")?.scrollIntoView({behavior:lessMotion?"auto":"smooth",block:"start"})));}
    }catch(e){if(runId===cancel.current)setError(e instanceof Error?e.message:"Search failed");}
    finally{if(runId===cancel.current)setLoading(false);}
  },[currentQuery,loading,lessMotion]);
  const changeWorld=(key:WorldKey)=>{cancel.current++;setLoading(false);setWorldKey(key);setResponse(null);setError("");setCustomMode(false);setCustomQuery("");};
  return <div className="observatory" style={{"--world-accent":world.accent} as React.CSSProperties}>
    <a href="#obs-main" className="obs-skip">Skip to content</a>
    <header className="obs-nav"><button className="obs-mark" onClick={()=>{goTo("explore");reset();}} aria-label="EvidenceSearch home"><span className="obs-symbol"><span/></span><span>Evidence<span className="obs-brand-accent">Search</span><small>THE OBSERVATORY</small></span></button>
      <nav className="obs-navlinks" aria-label="Observatory navigation"><button className={view==="explore"?"chosen":""} onClick={()=>goTo("explore")}>Explore</button><button className={view==="performance"?"chosen":""} onClick={()=>goTo("performance")}>Performance</button><button className={view==="methodology"?"chosen":""} onClick={()=>goTo("methodology")}>Methodology</button></nav>
      <div className="obs-nav-end"><span className={`obs-engine-dot ${ready==="offline"?"off":""}`}/><span className="obs-engine-state">{ready==="ready"?"SCI-FACT ENGINE LIVE":ready==="checking"?"CONNECTING":"LOCAL ENGINE OFFLINE"}</span></div>
    </header>
    <main id="obs-main">
    <AnimatePresence mode="wait">
      {view==="explore"?<motion.div key="explore" initial={lessMotion?false:{opacity:0}} animate={{opacity:1}} exit={lessMotion?undefined:{opacity:0}}>
        {!response&&<section className="obs-world-selection obs-world-first" aria-label="Choose research world">
          <div className="obs-world-first-header"><span className="obs-overline">01 / SELECT A RESEARCH WORLD</span><p>Choose a field to shape the experience. Every query still searches the same SciFact collection.</p></div>
          <div className="obs-world-options" role="group" aria-label="Research topic">{WORLDS.map(w=><button className={`obs-world-option ${worldKey===w.key?"active":""}`} key={w.key} onClick={()=>changeWorld(w.key)} aria-pressed={worldKey===w.key}><WorldGlyph kind={w.key} color={w.accent}/><strong>{w.name}</strong>{worldKey===w.key?<Check size={16}/>:<ArrowUpRight size={14}/>}</button>)}</div>
        </section>}
        <section className={`obs-hero ${response?"obs-hero-results":""}`}>
          <div className="obs-hero-copy"><div className="obs-kicker"><span className="obs-kicker-line"/> SCIENTIFIC KNOWLEDGE / REIMAGINED</div>
            <h1>{response?<>The evidence<br/><em>emerges.</em></>:<>Curiosity has<br/><em>a universe.</em></>}</h1>
            <p>Follow a question into the literature. Explore real abstracts, trace relevance, and see what different retrieval models reveal.</p>
            {response&&<button className="obs-quiet-action" onClick={reset}><ArrowLeft size={17}/> Choose another world</button>}
          </div><div className="obs-hero-visual" aria-label={`${world.name} inspired original animation`}><AnimatePresence mode="wait"><motion.div key={world.key} className="obs-world-stage" initial={lessMotion?false:{opacity:0,scale:1.04}} animate={{opacity:1,scale:1}} exit={lessMotion?undefined:{opacity:0,scale:.97}} transition={{duration:.65}}><WorldCanvas world={world.key} variant="hero"/></motion.div></AnimatePresence><div className="obs-world-annotation"><span>{world.label}</span><span>ORIGINAL VISUAL STUDY</span></div></div>
          <div className="obs-hero-bottom"><span>001 — A NEW WAY TO EXPLORE</span><span>{world.name.toUpperCase()} <span className="obs-mini-diamond"/></span></div>
        </section>
        {!response&&<section className="obs-world-details">          <div className="obs-choice-panel"><div><span className="obs-kicker">SELECTED STUDY / {world.name.toUpperCase()}</span><h3>{world.title}</h3><p>{world.description}</p><blockquote>{currentQuery}</blockquote>{world.coverage==="exploratory"&&!customMode&&<span className="obs-coverage-note">Exploratory topic — SciFact coverage may be limited. Returned papers may not address this topic.</span>}</div>
            <div className="obs-choice-actions"><button className="obs-cta" disabled={loading||currentQuery.trim().length<3} onClick={()=>void run()}>{loading?<LoaderCircle className="obs-spin" size={17}/>:<Compass size={19}/>} {loading?"Mapping evidence…":"Enter the Observatory"} <ArrowRight size={18}/></button><button className="obs-custom-toggle" onClick={()=>setCustomMode(v=>!v)} aria-expanded={customMode}>{customMode?"Use curated question":"Try a custom question"} <ChevronDown size={15}/></button>{customMode&&<textarea aria-label="Your own scientific question" value={customQuery} maxLength={600} onChange={e=>setCustomQuery(e.target.value)} placeholder="Ask a question within the SciFact corpus…"/>}</div>
          </div>
          {error&&<div className="obs-error" role="alert"><strong>Unable to retrieve real documents.</strong> {error}<p>Run the local FastAPI backend and verify model assets. No substitute articles are generated.</p></div>}
          {loading&&<div className="obs-mapping-loader"><div className="obs-orbit-loader"/><span>Encoding your query · finding candidates · reranking originals</span></div>}
        </section>}
        {response&&<><section className="obs-query-band"><span className="obs-overline">THE QUESTION / {world.name.toUpperCase()}</span><p>{response.query}</p><button onClick={reset}>Change question <RotateCcw size={16}/></button></section><Atlas key={response.query} data={response} world={world} method={method} onMethodChange={setMethod} onInspect={setReader}/><section className="obs-archive-section"><div className="obs-section-heading"><div><span className="obs-kicker">03 / THE ORIGINAL SOURCES</span><h2>The papers,<br/><em>unfiltered.</em></h2><p>Read real indexed abstracts in the order returned by your chosen lens.</p></div><span className="obs-micro-stat">SCIFACT / 5,183 DOCUMENTS</span></div><div className="obs-paper-collection">{response.methods[method].map((p,i)=><motion.button key={p.document_id} initial={lessMotion?false:{opacity:0,y:16}} whileInView={{opacity:1,y:0}} viewport={{once:true,amount:.1}} transition={{delay:Math.min(i*.03,.2)}} className="obs-document-row" onClick={()=>setReader(p)}><span className="obs-doc-num">{String(i+1).padStart(2,"0")}</span><div><span className="obs-source-tag">SCIFACT / {p.document_id}</span><h3>{p.title}</h3><p>{p.abstract.slice(0,235)}{p.abstract.length>235?"…":""}</p></div><ArrowUpRight size={23}/></motion.button>)}</div><p className="obs-method-foot">Documents are retrieved from the indexed SciFact corpus, not the live web. Relevance does not establish support, refutation, or scientific correctness.</p></section></>}
      </motion.div>:view==="performance"?<motion.div key="performance" initial={lessMotion?false:{opacity:0,y:14}} animate={{opacity:1,y:0}} exit={lessMotion?undefined:{opacity:0}}><Performance world={world}/></motion.div>:<motion.div key="methodology" initial={lessMotion?false:{opacity:0,y:14}} animate={{opacity:1,y:0}} exit={lessMotion?undefined:{opacity:0}}><Methodology world={world}/></motion.div>}
    </AnimatePresence>
    </main>
    <footer className="obs-footer"><span>EvidenceSearch / The Observatory</span><span>Real retrieval. Original abstracts. No generated scientific claims.</span><span>2026 / EXPERIMENTAL EXPERIENCE</span></footer>
    <AnimatePresence>{reader&&<Reader key={reader.document_id} paper={reader} onClose={()=>setReader(null)}/>}</AnimatePresence>
  </div>;
}
