export type MethodKey = "bm25" | "hybrid" | "reranked";
export const METHODS: MethodKey[] = ["reranked", "hybrid", "bm25"];
export const METHOD_LABEL: Record<MethodKey, string> = {
  bm25: "BM25", hybrid: "Hybrid RRF", reranked: "EvidenceSearch",
};
export interface Paper {
  document_id: string;
  rank: number;
  score: number;
  title: string;
  abstract: string;
  method: MethodKey;
}
export interface PaperTrace {
  document_id: string;
  title: string;
  ranks: Record<MethodKey, number | null>;
}
export interface SearchResponse {
  query: string;
  collection: { id: string; name: string; document_count: number };
  methods: Record<MethodKey, Paper[]>;
  traces: PaperTrace[];
  candidate_count: number;
  elapsed_ms: number;
  score_note: string;
}
export type MetricKey = "nDCG@10" | "Recall@10" | "MRR@10";
export interface BenchmarkData {
  evaluation: string;
  query_count: number;
  metrics: Record<"BM25" | "Hybrid RRF" | "CE · RRF@100", Record<MetricKey, number>>;
  paired_vs_bm25: Array<Record<string, unknown>>;
  latency: {warm_median_ms?: number; warm_p95_ms?: number; observed_rss_mb_max?: number};
  caveat: string;
}
