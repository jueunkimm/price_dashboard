"""정적 JSON export — 백엔드 없는 GitHub Pages 배포용.

모든 API 응답을 JSON 파일로 생성한다. 파라미터형(제품검색·필터옵션·브랜드비교)은
`products.json` 한 벌로 내보내 프론트가 브라우저에서 필터링한다.

실행:  python -m app.export_static [출력디렉터리]
기본 출력: frontend/public/data
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path

from sqlalchemy import select

from app import aggregation, qa_report, report
from app.database import SessionLocal
from collector.enrich_subcategory import display_subtype
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
    """제품 + 현재가/변동/용량/몰 (프론트 필터용, dedup 전).

    별매품(부품/소모품)도 포함하되 is_accessory 플래그를 실어 프론트에서 배지·토글로
    구분한다. 가격 통계/비교/포지셔닝은 프론트에서 is_accessory를 제외(렌탈·오배치와 동일).
    """
    products = aggregation._load_products(db, False, exclude_rental=False, exclude_accessory=False)
    snaps = aggregation._snaps_by_product(db, [p.id for p in products])
    cats = {c.id: c.name for c in db.scalars(select(Category)).all()}
    brands = {b.id: b.name for b in db.scalars(select(Brand)).all()}

    # 카테고리별 세부유형 빈도(non-null) + 전체 수 — 폴백 판단에 사용
    sub_dist: dict[int, Counter] = defaultdict(Counter)
    cat_total: dict[int, int] = defaultdict(int)
    for p in products:
        cat_total[p.category_id] += 1
        if p.sub_category:
            sub_dist[p.category_id][p.sub_category] += 1

    # 네이버 category4 커버리지가 충분한(≥40%) 카테고리만 '진짜 세부유형 보유'로 간주.
    # 피부케어기기·두피케어기기처럼 category4가 대부분 비어 소수 오분류(기타수작업공구 등)만
    # 있는 카테고리는 폴백을 끄고 세부유형을 비워둔다(노이즈 라벨 방지).
    has_real_subtypes = {
        cid for cid, cnt in sub_dist.items()
        if sum(cnt.values()) >= max(3, 0.4 * cat_total[cid])
    }

    # 카테고리별 대표 네이버 상위분류(category3) — 오배치(off_category) 판정용
    navercat_dist: dict[int, Counter] = defaultdict(Counter)
    for p in products:
        if p.naver_cat:
            navercat_dist[p.category_id][p.naver_cat] += 1
    dominant_navercat = {
        cid: c.most_common(1)[0][0] for cid, c in navercat_dist.items() if sum(c.values()) >= 5
    }

    rows = []
    for p in products:
        ch = aggregation.product_change(snaps.get(p.id, []))
        if ch["current_price"] is None:
            continue
        # DB는 null 유지(다음 수집의 enrich가 정확히 채우게) — 표시값만 폴백 분류.
        # 진짜 세부유형이 없는 카테고리는 폴백하지 않음(null 유지).
        sub = p.sub_category
        if not sub and p.category_id in has_real_subtypes:
            sub = display_subtype(
                cats.get(p.category_id), p.model_name, sub_dist.get(p.category_id)
            )
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
                "is_accessory": p.is_accessory,
                "model_key": p.model_key,
                "sub_category": sub,
                # 네이버 상위분류가 카테고리 대표와 다르면 오배치(가격 통계에서 제외)
                "off_category": bool(
                    p.naver_cat
                    and dominant_navercat.get(p.category_id)
                    and p.naver_cat != dominant_navercat[p.category_id]
                ),
                "capacity_band": aggregation._band(p),
                "mall": aggregation._latest_mall(snaps.get(p.id, [])),
                "image_url": p.image_url,
                "link": p.link,
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
        _write(out, "qa_report.json", qa_report.build_qa_report(db))
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
    # 평균 변동률: '카테고리 중앙값의 평균'은 대부분 제품이 무변동(0%)이라 항상 0.00%로 수렴해
    # 실제 시장 움직임을 못 담음. → 제품(모델) 단위 변동률 평균으로 계산.
    # ranking 모집단 재사용(렌탈·부품 제외 + 모델 dedup + 무변동 null 제외) — top_up/down과 동일 기준.
    changes = [r["change_pct"] for r in ranking if r.get("change_pct") is not None]
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
