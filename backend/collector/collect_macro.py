"""환율 수집(F12) — 한국은행 ECOS에서 USD/KRW를 macro_metric에 적재.

실행:  python -m collector.collect_macro [--days 90]
ECOS_API_KEY 필요(.env). 멱등 upsert(metric_type, period 기준), 출처='ecos'.
"""
from __future__ import annotations

import sys
from datetime import date, datetime, timedelta

from sqlalchemy import select

from app.database import Base, SessionLocal, engine
from app.models import MacroMetric
from collector.ecos_client import EcosClient


def _parse_days(argv: list[str]) -> int:
    if "--days" in argv:
        try:
            return int(argv[argv.index("--days") + 1])
        except (ValueError, IndexError):
            pass
    return 90


def run_macro(days: int = 90) -> dict:
    Base.metadata.create_all(bind=engine)
    end = date.today()
    start = end - timedelta(days=days)
    db = SessionLocal()
    client = EcosClient()
    upserts = 0
    try:
        rows = client.usd_krw(start.strftime("%Y%m%d"), end.strftime("%Y%m%d"))
        for r in rows:
            period = datetime.strptime(r["period"], "%Y%m%d").date()
            existing = db.scalar(
                select(MacroMetric).where(
                    MacroMetric.metric_type == "usd_krw", MacroMetric.period == period
                )
            )
            if existing:
                existing.value = r["value"]
                existing.source = "ecos"  # 합성→실데이터 출처 갱신
            else:
                db.add(
                    MacroMetric(
                        metric_type="usd_krw",
                        period=period,
                        value=r["value"],
                        source="ecos",
                    )
                )
            upserts += 1
        db.commit()
        return {"metric": "usd_krw", "points": len(rows), "upserts": upserts}
    finally:
        db.close()


if __name__ == "__main__":
    import json

    print(json.dumps(run_macro(_parse_days(sys.argv)), ensure_ascii=False, indent=2))
