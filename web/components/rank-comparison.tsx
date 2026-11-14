"use client";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { ArrowDownRight, ArrowRight, ArrowUpRight, X } from "lucide-react";
import { useMemo, useState } from "react";
import type { MethodKey, PaperTrace, SearchResponse } from "@/lib/types";

const stages: Array<{key:MethodKey;label:string;x:number}> = [
  {key:"bm25",label:"BM25",x:200},{key:"hybrid",label:"Hybrid RRF",x:450},{key:"reranked",label:"Cross-encoder",x:700},
];
const positionY = (rank: number | null) => 93 + (Math.min(rank ?? 11, 11) - 1) * 25;

export function RankComparison({data,onClose}:{data:SearchResponse;onClose:()=>void}) {
  const [chosen,setChosen] = useState(data.traces[0]?.document_id || "");
  const [all,setAll] = useState(false);
  const lessMotion = useReducedMotion();
  const selected = useMemo(() => data.traces.find(p=>p.document_id===chosen) || data.traces[0], [chosen,data.traces]);
  const traces = all ? data.traces : selected ? [selected] : [];
  if (!selected) return null;
  const before=selected.ranks.bm25, after=selected.ranks.reranked;
  const change=before!=null && after!=null ? before-after : null;
  const pathFor=(trace:PaperTrace) => {
    const pts=stages.map(stage => ({x:stage.x,y:positionY(trace.ranks[stage.key])}));
    return `M ${pts[0].x} ${pts[0].y} L ${pts[1].x} ${pts[1].y} L ${pts[2].x} ${pts[2].y}`;
  };
  return <motion.section className="comparison-panel" initial={lessMotion?false:{opacity:0,y:22}} animate={{opacity:1,y:0}} exit={lessMotion?{}:{opacity:0,y:16}} aria-label="Document ranking comparison">
    <div className="compare-head"><div><span className="eyebrow">RANK EXPLORER · SAME QUERY, THREE ALGORITHMS</span><h2>Watch the evidence move.</h2><p>Follow a real SciFact document through our retrieval system. Higher rank means earlier in the results—not more scientifically correct.</p></div><button onClick={onClose} aria-label="Close ranking comparison" className="icon-button close-compare"><X size={20}/></button></div>
    <div className="compare-controls"><label className="select-group">TRACK A PAPER
      <select value={selected.document_id} onChange={e=>setChosen(e.target.value)}>
        {data.traces.map(t=><option key={t.document_id} value={t.document_id}>{t.title} · {t.document_id}</option>)}
      </select>
    </label><div className="segmented" role="group" aria-label="Chart display mode"><button className={!all?"active":""} onClick={()=>setAll(false)}>Focus</button><button className={all?"active":""} onClick={()=>setAll(true)}>All paths</button></div></div>
    <div className="rank-svg-wrap">
      <svg viewBox="0 0 860 420" role="img" aria-label={`Ranking of ${selected.title}: BM25 ${before??'not in top 100'}, Hybrid ${selected.ranks.hybrid??'not in top 100'}, Cross-encoder ${after??'not in top 100'}`}>
        <defs><linearGradient id="selectedPath" x1="0" x2="1"><stop offset="0%" stopColor="#70bce3"/><stop offset="100%" stopColor="#75ddbb"/></linearGradient></defs>
        {stages.map((stage)=><text key={stage.key} x={stage.x} y={39} textAnchor="middle" className="chart-method">{stage.label}</text>)}
        {[1,2,3,4,5,6,7,8,9,10,11].map((rank)=><g key={rank}><line x1="128" x2="760" y1={positionY(rank)} y2={positionY(rank)} stroke="#547181" strokeOpacity={rank===11?0.36:0.2} strokeDasharray="5 7"/><text x="105" y={positionY(rank)+4} textAnchor="end" className="chart-rank">{rank===11?"11+":`#${rank}`}</text></g>)}
        {traces.map((trace)=> <g key={trace.document_id} opacity={trace.document_id===chosen?1:0.19}>
          <motion.path d={pathFor(trace)} stroke={trace.document_id===chosen?"url(#selectedPath)":"#9bb0c7"} strokeWidth={trace.document_id===chosen?5:2} strokeLinecap="round" strokeLinejoin="round" fill="none" initial={lessMotion?false:{pathLength:0}} animate={{pathLength:1}} transition={{duration:0.85}}/>
          {stages.map(stage=><motion.circle key={stage.key} cx={stage.x} cy={positionY(trace.ranks[stage.key])} r={trace.document_id===chosen?8:4} fill={trace.document_id===chosen?"#8de2c8":"#66869c"} stroke="#10212d" strokeWidth="3" initial={lessMotion?false:{scale:0}} animate={{scale:1}} transition={{delay:lessMotion?0:0.2}}/>)}
        </g>)}
        <text x="444" y="404" textAnchor="middle" className="chart-bottom">RETRIEVAL METHOD →</text>
      </svg>
      <div className="rank-overflow-hint">Rank 11+ means outside the first ten results; the complete position appears below.</div>
    </div>
    <AnimatePresence mode="wait"><motion.div key={selected.document_id} className="compare-spotlight" initial={lessMotion?false:{opacity:0,y:12}} animate={{opacity:1,y:0}} exit={lessMotion?{}:{opacity:0,y:-10}}>
      <div><span className="eyebrow">SELECTED DOCUMENT · {selected.document_id}</span><h3>{selected.title}</h3></div>
      <div className="rank-movement"><div className="rank-pill"><small>BM25</small><strong>{before ? `#${before}`:"—"}</strong></div><ArrowRight size={16}/><div className="rank-pill"><small>Hybrid</small><strong>{selected.ranks.hybrid ? `#${selected.ranks.hybrid}`:"—"}</strong></div><ArrowRight size={16}/><div className="rank-pill"><small>Reranked</small><strong>{after ? `#${after}`:"—"}</strong></div></div>
      <div className={`movement-note ${change===null?"":change>=0?"positive":"negative"}`}>
        {change===null?"Not present in both ranking pools":change===0?"Same position":change>0?`Moved up ${change} positions`:`Moved down ${Math.abs(change)} positions`}
        {change!==null&&(change>0?<ArrowUpRight size={16}/>:change<0?<ArrowDownRight size={16}/>:null)}
      </div>
    </motion.div></AnimatePresence>
    <p className="fine-print">Methods share the same query but rank differently. A rank change alone does not demonstrate a causal explanation or a judgment of scientific truth.</p>
  </motion.section>;
}
