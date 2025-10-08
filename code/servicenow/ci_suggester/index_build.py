# code/ci_suggester/index_build.py
import os, json, faiss, numpy as np
from pathlib import Path
from sentence_transformers import SentenceTransformer

from datetime import datetime, timezone  # only used if you add timestamps later

DATA_DIR = Path(os.getenv("DATA_DIR", "data"))
MODEL_ID = os.getenv("EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")

def run():
    data = json.loads((DATA_DIR / "ci_corpus.json").read_text(encoding="utf-8"))
    texts = [d["text"] for d in data]
    meta  = [d["meta"] for d in data]

    model = SentenceTransformer(MODEL_ID)
    emb = model.encode(texts, normalize_embeddings=True, convert_to_numpy=True).astype("float32")

    index = faiss.IndexFlatIP(emb.shape[1])
    index.add(emb)

    faiss.write_index(index, str(DATA_DIR / "index.faiss"))
    (DATA_DIR / "meta.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")

if __name__ == "__main__":
    run()
