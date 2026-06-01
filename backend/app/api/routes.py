"""REST API(D-5) — 모든 조회 API에 is_own_brand 필터(own_only) 지원."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import aggregation, report
from app.database import get_db
from app.models import (
    Alert,
    AlertRule,
    Brand,
    Category,
    CollectionLog,
    DemandMetric,
    MacroMetric,
    MarketEvent,
    PriceSnapshot,
    Product,
)

router = APIRouter(prefix="/api")


@router.get("/health")
def health(db: Session = Depends(get_db)):
    return {
        "status": "ok",
        "categories": db.scalar(select(func.count()).select_from(Category)),
        "products": db.scalar(select(func.count()).select_from(Product)),
        "snapshots": db.scalar(select(func.count()).select_from(PriceSnapshot)),
    }


@router.get("/kpi")
def kpi(own_only: bool = Query(False), db: Session = Depends(get_db)):
    """상단 KPI 요약 바(E-1)."""
    cats = aggregation.category_overview(db, is_own_only=own_only)
    ranking = aggregation.movement_ranking(db, is_own_only=own_only, limit=1000)
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


@router.get("/categories")
def categories(own_only: bool = Query(False), db: Session = Depends(get_db)):
    """카테고리 그리드(E-2, F1·F2)."""
    return aggregation.category_overview(db, is_own_only=own_only)


@router.get("/ranking")
def ranking(
    own_only: bool = Query(False),
    limit: int = Query(50, le=500),
    db: Session = Depends(get_db),
):
    """변동 랭킹 테이블(E-4, F4)."""
    return aggregation.movement_ranking(db, is_own_only=own_only, limit=limit)


@router.get("/products/{product_id}/timeseries")
def product_timeseries(product_id: int, db: Session = Depends(get_db)):
    """추세 차트(E-3, F3)."""
    return aggregation.product_timeseries(db, product_id)


@router.get("/positioning")
def positioning(db: Session = Depends(get_db)):
    """쿠쿠 포지셔닝(F-C) — 카테고리 평균 대비(참고용)."""
    return aggregation.cuckoo_positioning(db)


@router.get("/positioning/segmented")
def positioning_segmented(db: Session = Depends(get_db)):
    """동급(용량 구간) 쿠쿠 포지셔닝(B-1) — like-for-like 의사결정용."""
    return aggregation.cuckoo_positioning_segmented(db)


@router.get("/brands")
def brands(db: Session = Depends(get_db)):
    """등록 브랜드 목록(자사/경쟁)."""
    rows = db.scalars(select(Brand)).all()
    return [{"id": b.id, "name": b.name, "is_own": b.is_own} for b in rows]


@router.get("/brand-comparison")
def brand_comparison(
    category_id: int = Query(..., description="소분류 카테고리 id"),
    capacity_band: str | None = Query(None),
    mall: str | None = Query(None),
    min_price: int | None = Query(None),
    max_price: int | None = Query(None),
    db: Session = Depends(get_db),
):
    """카테고리 내 브랜드별 가격/변동 비교(B-2) — 제품 목록과 동일 필터 반영."""
    return aggregation.brand_comparison(
        db,
        category_id,
        capacity_band=capacity_band,
        mall=mall,
        min_price=min_price,
        max_price=max_price,
    )


@router.get("/data-quality")
def data_quality(db: Session = Depends(get_db)):
    """데이터 신뢰성 현황(실측 vs 합성, 제외 품목 등)."""
    return aggregation.data_quality(db)


@router.get("/products")
def products(
    own_only: bool = Query(False),
    category_id: int | None = Query(None),
    q: str | None = Query(None, description="모델명 검색"),
    limit: int = Query(100, le=1000),
    db: Session = Depends(get_db),
):
    """제품 검색·필터(E-5, F5)."""
    stmt = select(Product)
    if own_only:
        stmt = stmt.where(Product.is_own_brand.is_(True))
    if category_id:
        stmt = stmt.where(Product.category_id == category_id)
    if q:
        stmt = stmt.where(Product.model_name.ilike(f"%{q}%"))
    rows = db.scalars(stmt.limit(limit)).all()
    return [
        {
            "product_id": p.id,
            "model_name": p.model_name,
            "category_id": p.category_id,
            "brand_raw": p.brand_raw,
            "is_own_brand": p.is_own_brand,
            "is_rental": p.is_rental,
        }
        for p in rows
    ]


@router.get("/events")
def events(db: Session = Depends(get_db)):
    """프로모션/시즌 이벤트 캘린더(F10)."""
    rows = db.scalars(select(MarketEvent).order_by(MarketEvent.start_date)).all()
    return [
        {
            "id": e.id,
            "title": e.title,
            "event_type": e.event_type,
            "category_id": e.category_id,
            "start_date": e.start_date,
            "end_date": e.end_date,
            "note": e.note,
        }
        for e in rows
    ]


@router.get("/demand")
def demand(
    category_id: int = Query(..., description="소분류 카테고리 id"),
    db: Session = Depends(get_db),
):
    """카테고리 수요(검색) 트렌드(F7) — 데이터랩 상대지수 시계열."""
    rows = db.scalars(
        select(DemandMetric)
        .where(DemandMetric.category_id == category_id)
        .order_by(DemandMetric.period)
    ).all()
    search = [r for r in rows if r.metric_type == "search_trend"]
    shopping = [r for r in rows if r.metric_type == "shopping_click"]
    is_synthetic = any(r.source == "demo_synthetic" for r in search)
    return {
        "category_id": category_id,
        "is_synthetic": is_synthetic,
        "search": [{"date": r.period.isoformat(), "ratio": r.value} for r in search],
        "shopping": [{"date": r.period.isoformat(), "ratio": r.value} for r in shopping],
    }


@router.get("/alerts")
def alerts(
    limit: int = Query(30, le=200),
    own_only: bool = Query(False),
    db: Session = Depends(get_db),
):
    """생성된 알림 목록(F11)."""
    stmt = select(Alert).order_by(Alert.created_at.desc()).limit(limit)
    if own_only:
        stmt = select(Alert).where(Alert.is_own_brand.is_(True)).order_by(
            Alert.created_at.desc()
        ).limit(limit)
    rows = db.scalars(stmt).all()
    return [
        {
            "id": a.id,
            "title": a.title,
            "change_pct": a.change_pct,
            "is_own_brand": a.is_own_brand,
            "period": a.period,
            "dispatched": a.dispatched,
            "created_at": a.created_at,
        }
        for a in rows
    ]


@router.get("/alert-rules")
def alert_rules(db: Session = Depends(get_db)):
    rows = db.scalars(select(AlertRule)).all()
    return [
        {
            "id": r.id,
            "name": r.name,
            "scope": r.scope,
            "threshold_pct": r.threshold_pct,
            "direction": r.direction,
            "channel": r.channel,
            "is_active": r.is_active,
        }
        for r in rows
    ]


@router.get("/macro")
def macro(
    metric: str = Query("usd_krw"),
    db: Session = Depends(get_db),
):
    """거시지표 시계열(F12) — 기본 USD/KRW."""
    rows = db.scalars(
        select(MacroMetric)
        .where(MacroMetric.metric_type == metric)
        .order_by(MacroMetric.period)
    ).all()
    is_synthetic = any(r.source == "demo_synthetic" for r in rows)
    return {
        "metric": metric,
        "latest": rows[-1].value if rows else None,
        "is_synthetic": is_synthetic,
        "series": [{"date": r.period.isoformat(), "value": r.value} for r in rows],
    }


@router.get("/report/weekly")
def report_weekly(db: Session = Depends(get_db)):
    """주간 요약 리포트(F13)."""
    return report.weekly_report(db)


@router.get("/filter-options")
def filter_options(
    category_id: int | None = Query(None),
    db: Session = Depends(get_db),
):
    """사이드바 필터 옵션(용량 구간·브랜드·가격범위)."""
    return aggregation.filter_options(db, category_id)


@router.get("/product-search")
def product_search(
    category_id: int | None = Query(None),
    brand_id: int | None = Query(None),
    capacity_band: str | None = Query(None),
    min_price: int | None = Query(None),
    max_price: int | None = Query(None),
    own_only: bool = Query(False),
    exclude_rental: bool = Query(True),
    q: str | None = Query(None),
    mall: str | None = Query(None),
    limit: int = Query(200, le=1000),
    db: Session = Depends(get_db),
):
    """사이드바 필터 검색 — 조건별 제품 + 현재가/변동률/몰."""
    return aggregation.filter_products(
        db,
        category_id=category_id,
        brand_id=brand_id,
        capacity_band=capacity_band,
        min_price=min_price,
        max_price=max_price,
        own_only=own_only,
        exclude_rental=exclude_rental,
        q=q,
        mall=mall,
        limit=limit,
    )


@router.get("/collection-logs")
def collection_logs(limit: int = Query(20, le=100), db: Session = Depends(get_db)):
    """수집 로그(F6)."""
    rows = db.scalars(
        select(CollectionLog).order_by(CollectionLog.started_at.desc()).limit(limit)
    ).all()
    return [
        {
            "id": r.id,
            "started_at": r.started_at,
            "finished_at": r.finished_at,
            "status": r.status,
            "categories_done": r.categories_done,
            "products_collected": r.products_collected,
            "snapshots_inserted": r.snapshots_inserted,
            "message": r.message,
        }
        for r in rows
    ]
