"use client";
import { motion, useReducedMotion } from "motion/react";
import { Activity, ArrowUpRight, ChartNoAxesCombined, ChevronDown, Clock3, ShieldCheck, Target, Zap } from "lucide-react";
import { useEffect, useState } from "react";
import { apiJson } from "@/lib/http";
import { ScienceScene } from "@/components/science-scene";
import type { BenchmarkData, MetricKey } from "@/lib/types";

const metrics: Array<{key:MetricKey;label:string;caption:string;explain:string;example:string}> = [
  {key:"Recall@10", label:"Relevant papers found", caption:"Known relevant papers in the first 10", explain:"For each research claim, how much of the known relevant evidence shows up in the first ten search results? Higher means less relevant evidence gets buried.", example:"Imagine looking only at the first page of search results."},
  {key:"nDCG@10", label:"Ranking quality", caption:"The order of the first 10 results", explain:"Are papers judged relevant near the beginning of the list, where people are most likely to read them? Higher is better.", example:"The most useful results should appear early, not on page two."},
  {key:"MRR@10", label:"First relevant match", caption:"How early the first known relevant paper appears", explain:"If a user needs just one useful starting point, how close to the top of the list is the first judged relevant paper? Higher means earlier.", example:"Find a good starting paper without scrolling as far."},
];
const MODEL_ROWS: Array<{id:keyof BenchmarkData["metrics"];name:string}> = [
  {id:"BM25",name:"Traditional BM25"},{id:"Hybrid RRF",name:"Hybrid retrieval"},{id:"CE · RRF@100",name:"EvidenceSearch"},
];
export default function PerformancePage() {
  const [data,setData] = useState<BenchmarkData|null>(null);
  const [problem,setProblem] = useState("");
  const [metric,setMetric] = useState<MetricKey>("Recall@10");
  const [details,setDetails] = useState(false);
  const lessMotion=useReducedMotion();
  useEffect(()=>{apiJson<BenchmarkData>("/api/benchmarks").then(setData).catch(e=>setProblem(e instanceof Error?e.message:"Cannot load benchmark data"));},[]);
  const best = data?.metrics["CE · RRF@100"];
  const baseline = data?.metrics.BM25;
  const gain = best && baseline ? 100*(best["Recall@10"]-baseline["Recall@10"]) : null;
  const ciRow = data?.paired_vs_bm25.find(x=>x["Metric"]==="nDCG@10");
  return <div className="performance-page page-view">
    <header className="page-hero"><div><span className="eyebrow"><span className="small-line"/> MEASURED ON RESERVED QUERIES</span><h1>Proof, not <em>promises.</em></h1><p>Three retrieval methods. The same research claims. Results explained in language anyone can understand.</p></div><ScienceScene variant="performance"/></header>
    {problem&&<div className="error-panel" role="alert"><strong>Benchmark data unavailable</strong><p>{problem}</p><span>Start the Python API to load the measured Notebook 05 report. No sample figures are substituted.</span></div>}
    {!data&&!problem&&<p className="load-line">Loading verified evaluation artifacts…</p>}
    {data&&best&&baseline&&<>
      <section className="outcome-grid"><div className="outcome-primary"><span className="eyebrow">THE FIRST-PAGE DIFFERENCE</span><h2>Better results. <em>Less digging.</em></h2><p>On 647 reserved research claims, more known-relevant papers appeared in the first ten results.</p><div className="big-outcome"><strong aria-label={`${(best["Recall@10"]*100).toFixed(2)} percent of known-relevant evidence retrieved in the first ten results`}>{(best["Recall@10"]*100).toFixed(2)}<span>%</span></strong><div><span className="gain"><ArrowUpRight size={19}/> +{gain?.toFixed(2)} percentage points</span><small>More than conventional keyword ranking</small></div></div></div><div className="outcome-side"><div className="outcome-illustration"><img src="/visuals/lattice.svg" alt=""/></div><span className="eyebrow">HOW TO READ IT</span><p>Think of the first ten results as the first page of search. Higher recall means more of the papers judged relevant were found there.</p><small>Based on available SciFact labels, not proof of scientific correctness.</small></div></section>
      <section className="performance-chart"><div className="performance-top"><div><span className="eyebrow">THREE METHODS · ONE COMPARISON</span><h2>What actually improved?</h2><p>{metrics.find(m=>m.key===metric)?.explain}</p></div><div className="metric-tabs metric-tabs-readable" role="group" aria-label="Choose what to measure">{metrics.map(m=><button key={m.key} onClick={()=>setMetric(m.key)} className={metric===m.key?"selected":""} aria-pressed={metric===m.key}><strong>{m.label}</strong><small>{m.key}</small></button>)}</div></div>
        <div className="metric-plain-heading" aria-live="polite"><span className="mini-spark"/> {metrics.find(m=>m.key===metric)?.caption}</div><div className="bars">{MODEL_ROWS.map((row,i)=>{const value=data.metrics[row.id][metric];return <div key={row.id} className={`bar-row ${i===2?"winning":""}`}><div className="bar-name">{row.name}{i===2&&<span>SELECTED</span>}</div><div className="bar-track"><motion.div className="bar-fill" animate={{width:`${value*100}%`}} initial={lessMotion?false:{width:0}} transition={{duration:0.8,delay:i*0.09}}/></div><div className="bar-value">{metric==="Recall@10"?(value*100).toFixed(2)+"%":value.toFixed(4)}</div></div>})}</div>
        <div className="chart-foot"><span>{metrics.find(m=>m.key===metric)?.example}</span><span>Same 647 held-out queries · bars start at zero</span></div>
      </section>
      <section className="performance-lower"><article className="performance-fact"><div className="fact-icon"><Clock3 size={21}/></div><span className="eyebrow">SEARCH SPEED</span><h3>{data.latency.warm_median_ms ? (data.latency.warm_median_ms/1000).toFixed(2)+"s" : "Not reported"}</h3><p>Median warm CPU search in the local benchmark. Deployment latency will be measured separately.</p></article><article className="performance-fact"><div className="fact-icon"><ShieldCheck size={21}/></div><span className="eyebrow">EVALUATION PROTOCOL</span><h3>{data.query_count} claims</h3><p>Reserved SciFact training queries, excluded from method selection. The official test set was previously explored.</p></article></section>
      <div className="technical"><button className="technical-toggle" onClick={()=>setDetails(d=>!d)} aria-expanded={details}><span><Activity size={18}/> Detailed evaluation for engineers</span><ChevronDown size={19} className={details?"rotated":""}/></button>{details&&<div className="technical-body"><p>All three models were evaluated on the same reserved queries with fixed settings. These values are from the completed Notebook 05 report.</p><div className="table-wrap"><table><thead><tr><th>Method</th><th>nDCG@10</th><th>Recall@10</th><th>MRR@10</th></tr></thead><tbody>{MODEL_ROWS.map(row=><tr key={row.id}><th>{row.name}</th>{(["nDCG@10","Recall@10","MRR@10"] as MetricKey[]).map(k=><td key={k}>{data.metrics[row.id][k].toFixed(4)}</td>)}</tr>)}</tbody></table></div>{ciRow&&<p className="fine-print">Paired nDCG@10 lift vs BM25: {Number(ciRow["Mean difference"]).toFixed(4)} (95% bootstrap interval {Number(ciRow["CI95 low"]).toFixed(4)} to {Number(ciRow["CI95 high"]).toFixed(4)}). The uncertainty interval is specific to this sample and evaluation protocol.</p>}<p className="fine-print">{data.caveat}</p></div>}</div>
    </>}
  </div>;
}
