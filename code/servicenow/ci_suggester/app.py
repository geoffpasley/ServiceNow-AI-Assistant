# code/ci_suggester/app.py
import os, json, math, faiss, numpy as np
from pathlib import Path
from fastapi import FastAPI, Query
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer
from datetime import datetime, timezone

import _core.globe as globe
import _core.extension as extension

# Initialize shared core (logger, config, etc.)
globe.initialize()
DATA_DIR = Path(os.getenv("DATA_DIR", "data"))
MODEL_ID = os.getenv("EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")

app = FastAPI()
_model = None
_index = None
_meta = None

class Candidate(BaseModel):
    ci_sys_id: str
    ci_name: str
    score: float
    features: dict

def _load():
    global _model, _index, _meta
    _model = SentenceTransformer(MODEL_ID)
    _index = faiss.read_index(str(DATA_DIR / "index.faiss"))
    _meta  = json.loads((DATA_DIR / "meta.json").read_text(encoding="utf-8"))
    globe.logger.entry(
        message=f"[API] Loaded index with {len(_meta)} vectors",
        type="debug"
    )

def _parse_sn_utc(sn_dt_str: str) -> datetime:
    """
    ServiceNow usually returns UTC timestamps in 'YYYY-MM-DD HH:MM:SS' (no tz).
    We parse as naive and attach UTC tzinfo.
    """
    try:
        # Try flexible ISO first (just in case)
        dt_obj = datetime.fromisoformat(sn_dt_str.replace("Z", ""))
    except Exception:
        dt_obj = datetime.strptime(sn_dt_str, "%Y-%m-%d %H:%M:%S")
    # Attach UTC tz if naive
    if dt_obj.tzinfo is None:
        dt_obj = dt_obj.replace(tzinfo=timezone.utc)
    return dt_obj

def _rescore(sim, m):
    total = m["stats"].get("total", 0)
    success = m["stats"].get("success", 0)
    caused = m["stats"].get("caused_inc", 0)
    last = m["stats"].get("last_change")

    f_i = math.log(1 + total)

    # Recency with timezone-aware UTC arithmetic
    days = 365
    if last:
        try:
            when = _parse_sn_utc(last)
            days = (datetime.now(timezone.utc) - when).days
        except Exception:
            days = 365
    r_i = math.exp(-days / 90.0)

    denom = max(1, total)
    q_i = (success / denom) - 0.5 * (caused / denom)

    score = 0.35 * float(sim) + 0.3 * f_i + 0.15 * r_i + 0.2 * q_i
    return score, {"s_i": float(sim), "f_i": f_i, "r_i": r_i, "q_i": q_i, "total": total}

@app.on_event("startup")
def startup():
    _load()

@app.get("/suggest_ci", response_model=list[Candidate])
def suggest_ci(q: str = Query(...), k: int = 10):
    qv = _model.encode([q], normalize_embeddings=True, convert_to_numpy=True).astype("float32")
    sims, idx = _index.search(qv, k * 4)  # overfetch for rescoring
    rows = []
    for sim, i in zip(sims[0], idx[0]):
        m = _meta[int(i)]
        s, feats = _rescore(sim, m)
        rows.append(Candidate(
            ci_sys_id=m["sys_id"],
            ci_name=m["name"],
            score=s,
            features=feats
        ))
    rows.sort(key=lambda x: x.score, reverse=True)
    globe.logger.entry(
        message=f"[API] q='{q}' → returned {min(k, len(rows))} / {len(rows)}",
        type="debug"
    )
    return rows[:k]
