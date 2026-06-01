"""정적 JSON export — 백엔드 없는 GitHub Pages 배포용.

모든 API 응답을 JSON 파일로 생성한다. 파라미터형(제품검색·필터옵션·브랜드비교)은
`products.json` 한 벌로 내보내 프론트가 브라우저에서 필터링한다.

실행:  python -m app.export_static [출력디렉터리]
기본 출력: frontend/public/data
"""
from __future__ import annotations

import json
import sys
from datetime import date, datetime
from pathlib import Path

from sqlalchemy import select

from app import aggregation, report
from app.database import SessionLocal
from app.models import (
    Alert,
    Brand,
    Category,
    CollectionLog,
    DemandMetric,
    MarketEvent,
    PriceSnapshot,
    Product,
)

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT = ROOT / "frontend" / "public" / "data"


def _enc(o):
    if isinstance(o, (date, datetime)):
        return o.isoformat()
    raise TypeError(str(type(o)))


def _write(out: Path, name: str, data) -> None:
    (out / name).write_text(json.dumps(data, ensure_ascii=False, default=_enc), encoding="utf-8")


def _all_products(db) -> list[dict]:
    """부품 제외 전 제품 + 현재가/변동/용량/몰 (프론트 필터용, dedup 전)."""
    products = aggregation._load_products(db, False, exclude_rental=False, exclude_accessory=True)
    snaps = aggregation._snaps_by_product(db, [p.id for p in products])
    cats = {c.id: c.name for c in db.scalars(select(Category)).all()}
    brands = {b.id: b.name for b in db.scalars(select(Brand)).all()}
    rows = []
    for p in products:
        ch = aggregation.product_change(snaps.get(p.id, []))
        if ch["current_price"] is None:
            continue
        rows.append(
            {
                "product_id": p.id,
                "model_name": p.model_name,
                "category_id": p.category_id,
                "category_name": cats.get(p.category_id, ""),
                "brand_id": p.brand_id,
                "brand": brands.get(p.brand_id, "기타/미상") if p.brand_id else "기타/미상",
                "is_own_brand": p.is_own_brand,
                "is_rental": p.is_rental,
                "model_key": p.model_key,
                "capacity_band": aggregation._band(p),
                "mall": aggregation._latest_mall(snaps.get(p.id, [])),
                "current_price": ch["current_price"],
                "prev_price": ch["prev_price"],
                "change_pct": ch["change_pct"],
            }
        )
    return rows


def _timeseries(db) -> dict:
    out: dict[str, dict] = {}
    products = db.scalars(select(Product)).all()
    snaps = aggregation._snaps_by_product(db, [p.id for p in products])
    for p in products:
        daily = aggregation._daily_prices(snaps.get(p.id, []))
        if not daily:
            continue
        out[str(p.id)] = {
            "product_id": p.id,
            "model_name": p.model_name,
            "is_own_brand": p.is_own_brand,
            "series": [{"date": d.isoformat(), "price": daily[d]} for d in sorted(daily)],
        }
    return out


def _demand(db) -> dict:
    out: dict[str, dict] = {}
    rows = db.scalars(select(DemandMetric).order_by(DemandMetric.period)).all()
    by_cat: dict[int, dict] = {}
    for r in rows:
        d = by_cat.setdefault(r.category_id, {"search": [], "shopping": [], "synthetic": False})
        pt = {"date": r.period.isoformat(), "ratio": r.value}
        if r.metric_type == "search_trend":
            d["search"].append(pt)
            if r.source == "demo_synthetic":
                d["synthetic"] = True
        elif r.metric_type == "shopping_click":
            d["shopping"].append(pt)
    for cid, d in by_cat.items():
        out[str(cid)] = {
            "category_id": cid,
            "is_synthetic": d["synthetic"],
            "search": d["search"],
            "shopping": d["shopping"],
        }
    return out


def export_all(out_dir: Path | None = None) -> dict:
    out = out_dir or DEFAULT_OUT
    out.mkdir(parents=True, exist_ok=True)
    db = SessionLocal()
    try:
        cats = [
            {
                "category_id": c.id,
                "category_name": c.name,
                "has_own_lineup": c.has_own_lineup,
            }
            for c in db.scalars(
                select(Category).where(Category.level == 2).order_by(Category.name)
            ).all()
        ]
        _write(out, "meta.json", {"categories": cats, "generated_at": datetime.now().astimezone()})

        # 비파라미터 집계(서버 사전계산)
        _write(out, "kpi_all.json", aggregation_kpi(db, False))
        _write(out, "kpi_own.json", aggregation_kpi(db, True))
        _write(out, "categories_all.json", aggregation.category_overview(db, False))
        _write(out, "categories_own.json", aggregation.category_overview(db, True))
        _write(out, "ranking_all.json", aggregation.movement_ranking(db, False, 500))
        _write(out, "ranking_own.json", aggregation.movement_ranking(db, True, 500))
        _write(out, "positioning.json", aggregation.cuckoo_positioning(db))
        _write(out, "positioning_segmented.json", aggregation.cuckoo_positioning_segmented(db))
        _write(out, "brands.json", [
            {"id": b.id, "name": b.name, "is_own": b.is_own}
            for b in db.scalars(select(Brand)).all()
        ])
        _write(out, "events.json", [
            {
                "id": e.id, "title": e.title, "event_type": e.event_type,
                "category_id": e.category_id, "start_date": e.start_date,
                "end_date": e.end_date, "note": e.note,
            }
            for e in db.scalars(select(MarketEvent).order_by(MarketEvent.start_date)).all()
        ])
        from app.models import MacroMetric

        mrows = db.scalars(
            select(MacroMetric).where(MacroMetric.metric_type == "usd_krw").order_by(MacroMetric.period)
        ).all()
        _write(out, "macro.json", {
            "metric": "usd_krw",
            "latest": mrows[-1].value if mrows else None,
            "is_synthetic": any(r.source == "demo_synthetic" for r in mrows),
            "series": [{"date": r.period.isoformat(), "value": r.value} for r in mrows],
        })
        _write(out, "report.json", report.weekly_report(db))
        _write(out, "data_quality.json", aggregation.data_quality(db))
        _write(out, "alerts.json", [
            {
                "id": a.id, "title": a.title, "change_pct": a.change_pct,
                "is_own_brand": a.is_own_brand, "period": a.period,
                "dispatched": a.dispatched, "created_at": a.created_at,
            }
            for a in db.scalars(select(Alert).order_by(Alert.created_at.desc()).limit(200)).all()
        ])
        _write(out, "collection_logs.json", [
            {
                "id": r.id, "started_at": r.started_at, "finished_at": r.finished_at,
                "status": r.status, "categories_done": r.categories_done,
                "products_collected": r.products_collected,
                "snapshots_inserted": r.snapshots_inserted, "message": r.message,
            }
            for r in db.scalars(select(CollectionLog).order_by(CollectionLog.started_at.desc()).limit(20)).all()
        ])

        # 파라미터형(프론트 필터용)
        _write(out, "products.json", _all_products(db))
        _write(out, "demand.json", _demand(db))
        _write(out, "timeseries.json", _timeseries(db))

        files = sorted(p.name for p in out.glob("*.json"))
        return {"out_dir": str(out), "files": len(files)}
    finally:
        db.close()


def aggregation_kpi(db, own_only: bool) -> dict:
    """routes.kpi 로직 재현."""
    cats = aggregation.category_overview(db, is_own_only=own_only)
    ranking = aggregation.movement_ranking(db, is_own_only=own_only, limit=10000)
    changes = [c["median_change_pct"] for c in cats if c["median_change_pct"] is not None]
    anomalies = sum(c["anomaly_count"] for c in cats)
    top_up = max(ranking, key=lambda r: r["change_pct"], default=None)
    top_down = min(ranking, key=lambda r: r["change_pct"], default=None)
    out = {
        "avg_change_pct": round(sum(changes) / len(changes), 2) if changes else None,
        "anomaly_count": anomalies,
        "product_count": sum(c["product_count"] for c in cats),
        "top_up": top_up,
        "top_down": top_down,
    }
    if own_only:
        positioning = aggregation.cuckoo_positioning(db)
        pos_vals = [p["positioning_pct"] for p in positioning if p["positioning_pct"] is not None]
        out["own_avg_positioning_pct"] = round(sum(pos_vals) / len(pos_vals), 2) if pos_vals else None
    return out


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    print(json.dumps(export_all(target), ensure_ascii=False, indent=2))
