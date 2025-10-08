import _core.globe as globe
import _core.servicenow as serveicenow
import os, json
from pathlib import Path
from datetime import datetime, timedelta, timezone

class Process:
    def __init__(self):
        self.servicenow = serveicenow.API(max_retries=5, timeout=180)
        self.ci_table = globe.variable.get('ci_suggester', 'ci_table')
        self.max_changes_per_ci = int(globe.variable.get('ci_suggester', 'max_changes_per_ci'))
        self.days_back = int(globe.variable.get('ci_suggester', 'days_back'))
        self.data_dir = globe.variable.get('ci_suggester', 'data_dir')
    
    def run(self):
        # Build encoded date string in SN format (UTC, naive string)
        since_dt = datetime.now(timezone.utc) - timedelta(days=self.days_back)
        since_str = since_dt.strftime("%Y-%m-%d %H:%M:%S")

        # 1) Pull CIs (using your encoded query)
        ci_eq = "active=true"
        ci_records = self.servicenow.GET_all_table_records(table=self.ci_table, encoded_query=ci_eq) or []
        globe.logger.entry(
            message=f"[ETL] Retrieved {len(ci_records)} CIs from {self.ci_table}",
            type="debug"
        )

        corpus = []
        processed = 0

        for ci in ci_records:
            ci_id = ci.get("sys_id")
            if not ci_id:
                continue

            # 2) Pull related changes (last N days)
            ch_eq = f"cmdb_ci={ci_id}^sys_created_on>={since_str}"
            ch_fields = ["sys_id", "number", "cmdb_ci", "sys_created_on", "close_code", "u_caused_incident"]
            ch_records = self.servicenow.GET_all_table_records(
                table="change_request",
                encoded_query=ch_eq,
                fields=ch_fields
            ) or []

            # Latest change timestamp (string as returned by SN)
            last_change = None
            for c in ch_records:
                ts = c.get("sys_created_on")
                if ts and (last_change is None or ts > last_change):
                    last_change = ts

            # Latest change timestamp (string as returned by SN)
            last_change = None
            for c in ch_records:
                ts = c.get("sys_created_on")
                if ts and (last_change is None or ts > last_change):
                    last_change = ts

            # Build CI text profile
            # Include common fields + last MAX_CHANGES_PER_CI change texts (most recent first)
            ch_sorted = sorted(ch_records, key=lambda x: x.get("sys_created_on") or "", reverse=True)
            ch_sample = ch_sorted[:int(self.max_changes_per_ci)]
            change_text = " ".join(
                f"{(c.get('short_description') or '')} {(c.get('description') or '')}".strip()
                for c in ch_sample
            )

            blob_parts = [
                ci.get("name") or "",
                ci.get("description") or "",
                ci.get("comments") or "",
                f"env:{ci.get('u_environment','')}",
                f"service:{ci.get('u_service','')}",
                change_text
            ]
            blob = " ".join(p for p in blob_parts if p)

            corpus.append({
                "text": blob,
                "meta": {
                    "sys_id": ci_id,
                    "name": ci.get("name", ""),
                    "stats": {
                        "total": len(ch_records),
                        "success": sum(1 for c in ch_records if (c.get("close_code") or "").lower() == "successful"),
                        "caused_inc": sum(1 for c in ch_records if str(c.get("u_caused_incident","false")).lower() in ("true","1")),
                        "last_change": last_change
                    }
                }
            })

            processed += 1
            if processed % 200 == 0:
                globe.logger.entry(
                    message=f"[ETL] Processed {processed}/{len(ci_records)} CIs",
                    type="debug"
                )

        # Write corpus
        (Path(self.data_dir) / "ci_corpus.json").write_text(
            json.dumps(corpus, ensure_ascii=False), encoding="utf-8"
        )
        globe.logger.entry(
            message=f"[ETL] Wrote {len(corpus)} CI profiles → {(Path(self.data_dir) / 'ci_corpus.json')}",
            type="debug"
        )
