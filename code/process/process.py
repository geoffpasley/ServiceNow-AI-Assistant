import _core.extension as extension
from fastapi import FastAPI, Query
from pydantic import BaseModel
from typing import List
import faiss, numpy as np, json, math, datetime as dt
from sentence_transformers import SentenceTransformer

app = FastAPI()
model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

# Load CI corpus and metadata from disk (built by your ETL cron)
# ci_texts: list[str], ci_meta: list[dict] with keys: sys_id, name, stats:{total, success, caused_inc, last_change}
with open("ci_corpus.json","r",encoding="utf-8") as f:
    data = json.load(f)
ci_texts = [d["text"] for d in data]
ci_meta  = [d["meta"] for d in data]

emb = model.encode(ci_texts, normalize_embeddings=True)
index = faiss.IndexFlatIP(emb.shape[1])
index.add(np.array(emb, dtype=np.float32))

class Candidate(BaseModel):
    ci_sys_id: str
    ci_name: str
    score: float
    features: dict

def score_row(sim, meta):
    total = meta["stats"].get("total",0)
    success = meta["stats"].get("success",0)
    caused = meta["stats"].get("caused_inc",0)
    last = meta["stats"].get("last_change")
    f_i = math.log(1+total)
    if last:
        days = (dt.datetime.utcnow() - dt.datetime.fromisoformat(last.replace('Z',''))).days
    else:
        days = 365
    r_i = math.exp(-days/90.0)
    denom = max(1,total)
    q_i = (success/denom) - 0.5*(caused/denom)
    return 0.35*sim + 0.3*f_i + 0.15*r_i + 0.2*q_i, dict(s_i=sim,f_i=f_i,r_i=r_i,q_i=q_i,total=total)

@app.get("/suggest_ci", response_model=List[Candidate])
def suggest_ci(q: str = Query(...), k: int = 10):
    qv = model.encode([q], normalize_embeddings=True)
    sims, idx = index.search(np.array(qv, dtype=np.float32), k*4)  # overfetch
    rows = []
    for sim, i in zip(sims[0], idx[0]):
        meta = ci_meta[i]
        score, feats = score_row(float(sim), meta)
        rows.append(Candidate(ci_sys_id=meta["sys_id"], ci_name=meta["name"], score=score, features=feats))
    rows.sort(key=lambda x: x.score, reverse=True)
    return rows[:k]