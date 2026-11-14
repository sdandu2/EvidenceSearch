"use client";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { ArrowRight, Blend, Database, FileSearch, Layers3, Microscope, Search, ShieldCheck, SlidersHorizontal } from "lucide-react";
import { useState } from "react";
import { ScienceScene } from "@/components/science-scene";

const stages = [
 {number:"01",label:"Retrieve",intro:"Two complementary ways to find candidates",subtitle:"Keyword matching + neural embeddings",icon:Search,description:"BM25 looks for exact technical terms. A pretrained MiniLM model independently searches for semantically related language. Each returns 100 candidate abstracts."},
 {number:"02",label:"Combine",intro:"Merge separate perspectives",subtitle:"Reciprocal Rank Fusion · k = 60",icon:Blend,description:"Reciprocal Rank Fusion merges both lists without pretending that BM25 and neural similarity scores mean the same thing. The fused result contains the top 100 candidates."},
 {number:"03",label:"Rerank",intro:"Read the query and abstract together",subtitle:"MS MARCO MiniLM cross-encoder",icon:SlidersHorizontal,description:"A cross-encoder jointly scores each claim–abstract pair. It reorders the 100 fused candidates and yields the final EvidenceSearch ranking."},
 {number:"04",label:"Inspect",intro:"Return source documents, not invented answers",subtitle:"Original SciFact abstract and record ID",icon:FileSearch,description:"Users examine the original title and abstract, compare rankings if needed, and retain the document ID for traceability. A high rank is not a claim-verification verdict."},
];
export default function MethodologyPage(){
  const [stage,setStage]=useState(0);
  const reduceMotion=useReducedMotion();
  const ActiveIcon=stages[stage].icon;
  return <div className="method-page page-view">
    <header className="page-hero"><div><span className="eyebrow"><span className="small-line"/> INSIDE THE SYSTEM</span><h1>Nothing hidden. <em>Nothing invented.</em></h1><p>A clear look at how each search becomes a ranked list of source documents.</p></div><ScienceScene variant="method" /></header>
    <section className="method-flow"><div className="method-timeline" role="tablist" aria-label="Retrieval pipeline steps">{stages.map((s,i)=>{const Icon=s.icon;return <button key={s.number} onClick={()=>setStage(i)} role="tab" aria-selected={stage===i} className={`method-stage ${stage===i?"on":""}`}><div className="method-top"><span>{s.number}</span><Icon size={23}/></div><strong>{s.label}</strong><span className="stage-subline">{s.subtitle}</span>{stage===i&&<motion.span layoutId="method-active" className="stage-underline"/>}</button>})}</div>
      <AnimatePresence mode="wait"><motion.div key={stage} className="method-spotlight" initial={reduceMotion?false:{opacity:0,x:16}} animate={{opacity:1,x:0}} exit={reduceMotion?{}:{opacity:0,x:-16}}><div className="method-art"><img src={["/visuals/microstructure.svg","/visuals/lattice.svg","/visuals/wavefield.svg","/visuals/evidence-field.svg"][stage]} alt=""/><span><ActiveIcon size={27}/></span></div><div className="method-content"><span className="eyebrow">STEP {stages[stage].number}</span><h2>{stages[stage].intro}</h2><p>{stages[stage].description}</p><button className="text-action" onClick={()=>setStage((stage+1)%stages.length)}>{stage===3?"Back to retrieval":"Next stage"}<ArrowRight size={17}/></button></div></motion.div></AnimatePresence>
    </section>
    <section className="method-bottom"><div><Database size={22}/><h3>What is indexed</h3><p>5,183 abstracts from the SciFact benchmark. This is a curated research collection, not all scientific publications, and it is not live web search.</p></div><div><ShieldCheck size={22}/><h3>What ranking does not prove</h3><p>The system ranks potential evidence. It does not determine whether a scientific statement is true, supported, or refuted. Retrieval labels are incomplete.</p></div></section>
    <div className="method-source">Original benchmark: <a href="https://github.com/beir-cellar/beir" target="_blank" rel="noreferrer">BEIR / SciFact <ArrowRight size={14}/></a>. Methods evaluated in EvidenceSearch Notebooks 01–05.</div>
  </div>;
}
