# Evaluation protocol, results, and limitations

## Two different evaluation settings

### SciFact (existing benchmark)

The frozen SciFact pipeline was evaluated on a **reserved internal holdout of 647 queries**. On that particular split, cross-encoder + RRF achieved:

- nDCG@10: **0.6953**
- Recall@10: **0.8256**
- MRR@10: **0.6599**

These figures are not the same as official SciFact-test metrics. Do not describe them as such.

### Expanded five-domain corpus (exploratory)

A five-domain snapshot contains 5,192 globally unique papers. An exploratory comparison on **nine matched development questions**, using provisional AI-generated grades, produced judged-pool nDCG@10 **0.8746** for cross-encoder + RRF and **0.7703** for BM25. The observed difference was **+0.1044** (descriptive paired-bootstrap 95% interval **+0.0484 to +0.1614**).

**Do not interpret these as independently verified accuracy scores.** There were only nine questions; the labels were generated provisionally from abstracts, candidate pools were influenced by earlier retrievers, and many newly added documents were never judged. Results may be inflated or incomparable to end-to-end full-corpus rankings.

## What the labels mean

- **2:** directly addresses the question / provides substantive evidence
- **1:** relevant background or partial evidence
- **0:** does not meaningfully answer the question
- **?:** unresolved; insufficient information

No unjudged document is automatically labeled 0. The locked holdout is kept isolated from model selection. A public result should not say that a document scientifically **supports** or **refutes** a claim without a separate claim-verification evaluation.

## What the next benchmark needs

- A meaningfully larger set of independent queries, including hard counterexamples.
- Blinded or independently audited relevance grades.
- A balanced pool across lexical, dense, hybrid, and reranked methods.
- Actual top-k order metrics with published judgment coverage.
- Common-question comparisons, uncertainty estimates, and measured end-to-end latency on the target hardware.

## Engineering observations

A local five-domain smoke test observed individual requests of approximately **0.82–0.90 seconds**. This is not a p95 latency claim and not evidence about public hosting. The separate cross-encoder warm CPU scoring benchmark observed p50 ~999 ms and p95 ~1,153 ms on a particular local setup; it excludes some request overhead. Neither number should be promised as public production performance.
