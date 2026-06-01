"""주간 요약 리포트(F13) — 데이터에서 핵심 지표를 집계해 리포트 dict 생성.

API(/api/report/weekly)와 CLI(python -m app.report) 양쪽에서 사용.
"""
from __future__ import annotations

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import aggregation
from app.models import Alert, MacroMetric, Product


def weekly_report(db: Session) -> dict:
    cats = aggregation.category_overview(db, is_own_only=False)
    ranking = aggregation.movement_ranking(db, is_own_only=False, limit=10000)
    positioning = aggregation.cuckoo_positioning(db)

    changes = [c["median_change_pct"] for c in cats if c["median_change_pct"] is not None]
    top_movers = sorted(ranking, key=lambda r: abs(r["change_pct"]), reverse=True)[:10]
    own_count = db.scalar(
        select(func.count()).select_from(Product).where(Product.is_own_brand.is_(True))
    )
    pos_vals = [p["positioning_pct"] for p in positioning if p["positioning_pct"] is not None]
    latest_fx = db.scalar(
        select(MacroMetric)
        .where(MacroMetric.metric_type == "usd_krw")
        .order_by(MacroMetric.period.desc())
    )
    alert_count = db.scalar(
        select(func.count()).select_from(Alert).where(Alert.period == date.today())
    )

    return {
        "generated_for": date.today().isoformat(),
        "category_count": len(cats),
        "avg_category_change_pct": round(sum(changes) / len(changes), 2) if changes else None,
        "total_anomalies": sum(c["anomaly_count"] for c in cats),
        "own_product_count": own_count,
        "own_avg_positioning_pct": round(sum(pos_vals) / len(pos_vals), 2) if pos_vals else None,
        "usd_krw": latest_fx.value if latest_fx else None,
        "alerts_today": alert_count,
        "top_movers": [
            {
                "model_name": m["model_name"][:60],
                "category": m["category_name"],
                "change_pct": m["change_pct"],
                "is_own_brand": m["is_own_brand"],
            }
            for m in top_movers
        ],
    }


def to_markdown(rep: dict) -> str:
    lines = [
        f"# 주간 가격 트래킹 리포트 ({rep['generated_for']})",
        "",
        f"- 트래킹 카테고리: **{rep['category_count']}개**",
        f"- 카테고리 평균 변동률: **{rep['avg_category_change_pct']}%**",
        f"- 급변(임계 초과) 제품: **{rep['total_anomalies']}건**",
        f"- 쿠쿠 제품: **{rep['own_product_count']}개**, 평균 포지셔닝 **{rep['own_avg_positioning_pct']}%**",
        f"- 환율(USD/KRW): **{rep['usd_krw']}**",
        f"- 오늘 생성된 알림: **{rep['alerts_today']}건**",
        "",
        "## Top 변동 제품",
    ]
    for m in rep["top_movers"]:
        tag = "🟣쿠쿠 " if m["is_own_brand"] else ""
        lines.append(f"- {tag}[{m['category']}] {m['change_pct']:+.1f}% — {m['model_name']}")
    return "\n".join(lines)


if __name__ == "__main__":
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        print(to_markdown(weekly_report(db)))
    finally:
        db.close()
