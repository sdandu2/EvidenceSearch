"""Pre-flight audit of existing notebook artifacts; does not download weights."""
from pathlib import Path
from backend.engine import DATASET_SIZE, load_benchmarks, read_corpus, verified_embeddings, verify_frozen_selection


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    verify_frozen_selection(root)
    corpus = read_corpus(root / "data" / "scifact" / "corpus.jsonl")
    if len(corpus) != DATASET_SIZE:
        raise RuntimeError(f"Expected {DATASET_SIZE} docs; got {len(corpus)}")
    matrix = verified_embeddings(root, sorted(corpus))
    report = load_benchmarks(root)
    print(f"SciFact corpus: {len(corpus):,} verified documents")
    print(f"Cached document embeddings: {matrix.shape}")
    print(f"Notebook 05 holdout: {report['query_count']} queries")
    print("Ready for backend model initialization.")


if __name__ == "__main__":
    main()
