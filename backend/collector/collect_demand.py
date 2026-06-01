"""수요 수집(F7) — 두 신호를 demand_metric에 적재.

  - search_trend  : 데이터랩 통합검색어 트렌드(일반 검색 관심도)
  - shopping_click: 데이터랩 쇼핑인사이트 키워드 트렌드(쇼핑 클릭=구매의도 근접)

실행:  python -m collector.collect_demand [--days 90]
멱등: (category_id, period, metric_type) 기준 upsert.
"""
from __future__ import annotations

import sys
from datetime import date, datetime, timedelta

from sqlalchemy import select

from app.database import Base, SessionLocal, engine
from app.models import Category, DemandMetric
from collector.datalab_client import DatalabClient
from collector.shopping_insight_client import ShoppingInsightClient, cid_for


def _parse_days(argv: list[str]) -> int:
    if "--days" in argv:
        try:
            return int(argv[argv.index("--days") + 1])
        except (ValueError, IndexError):
            pass
    return 90


def _upsert(db, cat_id: int, metric_type: str, points: list[dict], source: str) -> int:
    n = 0
    for pt in points:
        period = datetime.strptime(pt["period"], "%Y-%m-%d").date()
        existing = db.scalar(
            select(DemandMetric).where(
                DemandMetric.category_id == cat_id,
                DemandMetric.period == period,
                DemandMetric.metric_type == metric_type,
            )
        )
        if existing:
            existing.value = pt["ratio"]
            existing.source = source
        else:
            db.add(
                DemandMetric(
                    category_id=cat_id,
                    metric_type=metric_type,
                    period=period,
                    value=pt["ratio"],
                    source=source,
                )
            )
        n += 1
    return n


def run_demand(days: int = 90) -> dict:
    Base.metadata.create_all(bind=engine)
    end = date.today()
    start_s, end_s = (end - timedelta(days=days)).isoformat(), end.isoformat()
    db = SessionLocal()
    search_client = DatalabClient()
    shop_client = ShoppingInsightClient()
    search_n = shop_n = cats_done = 0
    try:
        categories = list(db.scalars(select(Category).where(Category.level == 2)).all())
        for cat in categories:
            keyword = cat.search_keyword or cat.name
            # 1) 통합검색어 트렌드
            try:
                pts = search_client.search_trend(keyword, start_s, end_s)
                search_n += _upsert(db, cat.id, "search_trend", pts, "naver_datalab")
            except Exception as e:  # noqa: BLE001
                print(f"[demand] 검색트렌드 '{keyword}' 실패: {e}")
            # 2) 쇼핑인사이트 클릭 트렌드
            try:
                pts = shop_client.keyword_trend(keyword, cid_for(cat.name), start_s, end_s)
                shop_n += _upsert(db, cat.id, "shopping_click", pts, "naver_shopping_insight")
            except Exception as e:  # noqa: BLE001
                print(f"[demand] 쇼핑인사이트 '{keyword}' 실패: {e}")
            db.commit()
            cats_done += 1
            print(f"[demand] {cat.name}")
        return {
            "categories_done": cats_done,
            "search_upserts": search_n,
            "shopping_upserts": shop_n,
        }
    finally:
        db.close()


if __name__ == "__main__":
    import json

    print(json.dumps(run_demand(_parse_days(sys.argv)), ensure_ascii=False, indent=2))
