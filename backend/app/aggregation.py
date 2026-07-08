"""집계·변동률 계산(D단계) — 기획서 6장 정의 기준.

- 일간 변동률 = (당일가 − 전일가) / 전일가 × 100
- 카테고리 변동률 = 제품 변동률의 중앙값(이상치에 강함)
- 이상치 = |변동률| ≥ 임계치(기본 10%)
- 쿠쿠 포지셔닝 = (쿠쿠가 − 카테고리 평균가) / 평균가 × 100
"""
from __future__ import annotations

import statistics
from collections import defaultdict
from datetime import date, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Brand, Category, PriceSnapshot, Product


def _day(dt: datetime) -> date:
    return dt.date()


# 렌탈 월요금 오염 차단: 한 productId(네이버 가격비교)에 렌탈 오퍼가 끼면
# 제목에 '렌탈'이 없어도 lprice가 월요금(보통 일시불가의 2~10%)으로 떨어져
# 트렌드가 40만→1만처럼 비현실적으로 급락한다. 제목 기반 is_rental로는 못 잡으므로,
# 같은 제품의 최고가(=일시불 추정) 대비 일정 비율 미만 스냅샷은 오염으로 보고 제외한다.
# 0.2 = 정상 할인(통상 ≥30~40%)은 보존하고 렌탈 월요금(≤10%)만 걸러내는 안전 경계.
_RENTAL_MIN_FRACTION = 0.2


def _daily_prices(snaps: list[PriceSnapshot]) -> dict[date, int]:
    """제품의 일자별 대표가(해당일 마지막 스냅샷의 list_price).

    렌탈 월요금 오염가(제품 최고가의 20% 미만)는 제외해 가격 왜곡을 방지한다.
    """
    valid = [s for s in snaps if s.list_price]
    if not valid:
        return {}
    floor = max(s.list_price for s in valid) * _RENTAL_MIN_FRACTION
    by_day: dict[date, tuple[datetime, int]] = {}
    for s in valid:
        if s.list_price < floor:
            continue  # 렌탈/오염 의심가 제외(일시불 대비 비현실적 저가)
        d = _day(s.collected_at)
        if d not in by_day or s.collected_at > by_day[d][0]:
            by_day[d] = (s.collected_at, s.list_price)
    return {d: price for d, (_, price) in by_day.items()}


def _change_pct(curr: int, prev: int) -> float | None:
    if not prev:
        return None
    return round((curr - prev) / prev * 100, 2)


def product_change(snaps: list[PriceSnapshot]) -> dict:
    """제품 단위 현재가 + 일간 변동률."""
    daily = _daily_prices(snaps)
    if not daily:
        return {"current_price": None, "prev_price": None, "change_pct": None}
    days = sorted(daily)
    current = daily[days[-1]]
    prev = daily[days[-2]] if len(days) >= 2 else None
    return {
        "current_price": current,
        "prev_price": prev,
        "change_pct": _change_pct(current, prev) if prev is not None else None,
    }


def _category_dominant_navercat(db: Session) -> dict[int, str]:
    """카테고리별 '대표' 네이버 상위분류(category3). 다수결, 표본 5건 이상만."""
    from collections import Counter, defaultdict

    cc: dict[int, Counter] = defaultdict(Counter)
    prods = db.scalars(
        select(Product).where(
            Product.is_rental.is_(False), Product.is_accessory.is_(False)
        )
    ).all()
    for p in prods:
        if p.naver_cat:
            cc[p.category_id][p.naver_cat] += 1
    return {cid: c.most_common(1)[0][0] for cid, c in cc.items() if sum(c.values()) >= 5}


def is_offcategory(p: Product, dominant: dict[int, str]) -> bool:
    """네이버 상위분류가 그 카테고리의 대표 분류와 다르면 오배치(가격 왜곡 유발)."""
    d = dominant.get(p.category_id)
    return bool(p.naver_cat and d and p.naver_cat != d)


def _load_products(
    db: Session,
    is_own_only: bool,
    exclude_rental: bool = False,
    exclude_accessory: bool = False,
    exclude_offcat: bool = False,
) -> list[Product]:
    stmt = select(Product)
    if is_own_only:
        stmt = stmt.where(Product.is_own_brand.is_(True))
    if exclude_rental:
        # 렌탈 상품은 월렌탈료가 표시가로 잡혀 일시불가와 섞이면 평균/포지셔닝을 왜곡
        stmt = stmt.where(Product.is_rental.is_(False))
    if exclude_accessory:
        # 부품/소모품은 본품 비교 풀에서 제외
        stmt = stmt.where(Product.is_accessory.is_(False))
    products = list(db.scalars(stmt).all())
    if exclude_offcat:
        # 네이버 상위분류가 카테고리 대표와 다른 오배치 제품 제외(가격 평균 보호)
        dom = _category_dominant_navercat(db)
        products = [p for p in products if not is_offcategory(p, dom)]
    return products


def _dedup_by_model(rows: list[dict]) -> list[dict]:
    """같은 model_key의 몰별 중복 리스팅을 모델 단위 1건으로 축약(최저가 대표).

    rows: [{product, current_price, change_pct, ...}]. model_key 없으면 개별 유지.
    """
    groups: dict[str, dict] = {}
    out: list[dict] = []
    for r in rows:
        p = r["product"]
        key = p.model_key
        if not key:
            out.append(r)  # 모델키 없으면 개별 제품으로
            continue
        gkey = f"{p.category_id}:{key}"
        cur = groups.get(gkey)
        if cur is None or (r["current_price"] or 9e18) < (cur["current_price"] or 9e18):
            groups[gkey] = r
    out.extend(groups.values())
    return out


def _snaps_by_product(db: Session, product_ids: list[int]) -> dict[int, list[PriceSnapshot]]:
    out: dict[int, list[PriceSnapshot]] = defaultdict(list)
    if not product_ids:
        return out
    stmt = select(PriceSnapshot).where(PriceSnapshot.product_id.in_(product_ids))
    for s in db.scalars(stmt).all():
        out[s.product_id].append(s)
    return out


def category_overview(db: Session, is_own_only: bool = False) -> list[dict]:
    """카테고리(level=2)별 평균/중앙값/최저·최고가 + 중앙값 변동률(F1·F2).

    렌탈 상품은 가격 왜곡 방지를 위해 집계에서 제외.
    """
    products = _load_products(
        db, is_own_only, exclude_rental=True, exclude_accessory=True, exclude_offcat=True
    )
    snaps = _snaps_by_product(db, [p.id for p in products])

    # 카테고리별 제품 변동 집계 (모델 단위 dedup으로 몰별 중복 제거)
    raw_by_cat: dict[int, list[dict]] = defaultdict(list)
    for p in products:
        ch = product_change(snaps.get(p.id, []))
        if ch["current_price"] is None:
            continue
        raw_by_cat[p.category_id].append({"product": p, **ch})
    by_cat: dict[int, list[dict]] = {
        cid: _dedup_by_model(rows) for cid, rows in raw_by_cat.items()
    }

    cats = {c.id: c for c in db.scalars(select(Category).where(Category.level == 2)).all()}
    # 대분류(level=1) 이름 — 프론트 그룹핑/탐색용
    groups = {c.id: c.name for c in db.scalars(select(Category).where(Category.level == 1)).all()}
    # 자사 라인업(★)은 정적 시드 플래그가 아니라 '실제 매칭된 자사 제품 ≥1건'으로 판정.
    # 쿠쿠홈시스 라인업 확장(냉장고·세탁기·에어컨 등) 같은 변화를 수집 데이터가 자동 반영.
    own_cat_ids = set(
        db.scalars(
            select(Product.category_id)
            .where(Product.is_own_brand.is_(True), Product.is_accessory.is_(False))
            .distinct()
        ).all()
    )
    threshold = settings.anomaly_threshold_pct
    results = []
    for cat_id, rows in by_cat.items():
        cat = cats.get(cat_id)
        if not cat:
            continue
        prices = [r["current_price"] for r in rows]
        changes = [r["change_pct"] for r in rows if r["change_pct"] is not None]
        median_change = round(statistics.median(changes), 2) if changes else None
        anomalies = sum(1 for c in changes if abs(c) >= threshold)
        results.append(
            {
                "category_id": cat_id,
                "category_name": cat.name,
                "group": groups.get(cat.parent_id, "기타"),
                "has_own_lineup": cat_id in own_cat_ids,
                "product_count": len(rows),
                "avg_price": round(statistics.mean(prices)),
                "median_price": round(statistics.median(prices)),
                "min_price": min(prices),
                "max_price": max(prices),
                "median_change_pct": median_change,
                "anomaly_count": anomalies,
            }
        )
    results.sort(key=lambda r: (not r["has_own_lineup"], r["category_name"]))
    return results


def movement_ranking(
    db: Session,
    is_own_only: bool = False,
    limit: int = 50,
    include_rental: bool = False,
) -> list[dict]:
    """변동률 큰 순 제품 랭킹(F4). 기본적으로 부품·렌탈 제외, 모델 단위 dedup."""
    products = _load_products(
        db, is_own_only, exclude_rental=not include_rental, exclude_accessory=True
    )
    snaps = _snaps_by_product(db, [p.id for p in products])
    cats = {c.id: c.name for c in db.scalars(select(Category)).all()}

    raw = []
    for p in products:
        ch = product_change(snaps.get(p.id, []))
        if ch["change_pct"] is None:
            continue
        raw.append({"product": p, **ch})

    threshold = settings.anomaly_threshold_pct
    rows = []
    for r in _dedup_by_model(raw):
        p = r["product"]
        rows.append(
            {
                "product_id": p.id,
                "model_name": p.model_name,
                "category_name": cats.get(p.category_id, ""),
                "is_own_brand": p.is_own_brand,
                "is_rental": p.is_rental,
                "current_price": r["current_price"],
                "prev_price": r["prev_price"],
                "change_pct": r["change_pct"],
                "is_anomaly": abs(r["change_pct"]) >= threshold,
                "link": p.link,
            }
        )
    rows.sort(key=lambda r: abs(r["change_pct"]), reverse=True)
    return rows[:limit]


def _band(p: Product) -> str | None:
    from app.spec import band_for

    return band_for(p.capacity_value, p.capacity_unit)


def _latest_mall(snaps: list[PriceSnapshot]) -> str | None:
    """제품의 최신 스냅샷이 어느 몰(source)인지."""
    if not snaps:
        return None
    return max(snaps, key=lambda s: s.collected_at).source


def filter_products(
    db: Session,
    category_id: int | None = None,
    brand_id: int | None = None,
    capacity_band: str | None = None,
    min_price: int | None = None,
    max_price: int | None = None,
    own_only: bool = False,
    exclude_rental: bool = True,
    q: str | None = None,
    mall: str | None = None,
    limit: int = 200,
) -> list[dict]:
    """사이드바 필터용 — 조건에 맞는 제품 + 현재가/변동률/몰 반환(부품 제외, 모델 dedup)."""
    stmt = select(Product).where(Product.is_accessory.is_(False))
    if category_id:
        stmt = stmt.where(Product.category_id == category_id)
    if brand_id:
        stmt = stmt.where(Product.brand_id == brand_id)
    if own_only:
        stmt = stmt.where(Product.is_own_brand.is_(True))
    if exclude_rental:
        stmt = stmt.where(Product.is_rental.is_(False))
    if q:
        stmt = stmt.where(Product.model_name.ilike(f"%{q}%"))
    products = list(db.scalars(stmt).all())
    snaps = _snaps_by_product(db, [p.id for p in products])
    cats = {c.id: c.name for c in db.scalars(select(Category)).all()}
    brands = {b.id: b.name for b in db.scalars(select(Brand)).all()}

    raw = []
    for p in products:
        band = _band(p)
        if capacity_band and band != capacity_band:
            continue
        ch = product_change(snaps.get(p.id, []))
        price = ch["current_price"]
        if price is None:
            continue
        if min_price is not None and price < min_price:
            continue
        if max_price is not None and price > max_price:
            continue
        mall_name = _latest_mall(snaps.get(p.id, []))
        if mall and (mall_name or "") != mall:
            continue
        raw.append({"product": p, **ch, "band": band, "mall": mall_name})

    rows = []
    for r in _dedup_by_model(raw):
        p = r["product"]
        rows.append(
            {
                "product_id": p.id,
                "model_name": p.model_name,
                "category_name": cats.get(p.category_id, ""),
                "brand": brands.get(p.brand_id, "기타/미상") if p.brand_id else "기타/미상",
                "capacity_band": r["band"],
                "mall": r["mall"],
                "is_own_brand": p.is_own_brand,
                "is_rental": p.is_rental,
                "current_price": r["current_price"],
                "change_pct": r["change_pct"],
            }
        )
    rows.sort(key=lambda r: r["current_price"])
    return rows[:limit]


def filter_options(db: Session, category_id: int | None = None) -> dict:
    """사이드바 드롭다운 옵션 — 해당 카테고리(또는 전체)의 용량 구간·브랜드 목록."""
    stmt = select(Product).where(Product.is_accessory.is_(False))
    if category_id:
        stmt = stmt.where(Product.category_id == category_id)
    products = list(db.scalars(stmt).all())
    brand_ids = {p.brand_id for p in products if p.brand_id}
    brands = [
        {"id": b.id, "name": b.name, "is_own": b.is_own}
        for b in db.scalars(select(Brand).where(Brand.id.in_(brand_ids or [-1]))).all()
    ]
    brands.sort(key=lambda b: (not b["is_own"], b["name"]))
    bands = sorted({_band(p) for p in products if _band(p)})
    snaps = _snaps_by_product(db, [p.id for p in products])
    prices = [
        c["current_price"]
        for p in products
        for c in [product_change(snaps.get(p.id, []))]
        if c["current_price"] is not None
    ]
    # 몰(채널) 분포 — 많은 순
    mall_count: dict[str, int] = {}
    for p in products:
        m = _latest_mall(snaps.get(p.id, []))
        if m:
            mall_count[m] = mall_count.get(m, 0) + 1
    malls = [
        {"name": m, "count": c}
        for m, c in sorted(mall_count.items(), key=lambda x: -x[1])
    ]
    return {
        "capacity_bands": bands,
        "brands": brands,
        "malls": malls,
        "price_min": min(prices) if prices else 0,
        "price_max": max(prices) if prices else 0,
    }


def brand_comparison(
    db: Session,
    category_id: int,
    capacity_band: str | None = None,
    mall: str | None = None,
    min_price: int | None = None,
    max_price: int | None = None,
    exclude_rental: bool = True,
) -> list[dict]:
    """카테고리 내 브랜드별 가격/변동 비교(B-2) — 부품 제외, 모델 dedup.

    제품 목록과 일관되게 용량/판매몰/가격대/렌탈 필터를 동일 적용(own_only/brand는 비교 위해 미적용).
    """
    products = [
        p
        for p in _load_products(db, False, exclude_rental=exclude_rental, exclude_accessory=True)
        if p.category_id == category_id
    ]
    snaps = _snaps_by_product(db, [p.id for p in products])
    brands = {b.id: b for b in db.scalars(select(Brand)).all()}

    raw = []
    for p in products:
        if capacity_band and _band(p) != capacity_band:
            continue
        ch = product_change(snaps.get(p.id, []))
        if ch["current_price"] is None:
            continue
        if min_price is not None and ch["current_price"] < min_price:
            continue
        if max_price is not None and ch["current_price"] > max_price:
            continue
        if mall and (_latest_mall(snaps.get(p.id, [])) or "") != mall:
            continue
        raw.append({"product": p, **ch})

    by_brand: dict[str, list[dict]] = defaultdict(list)
    for r in _dedup_by_model(raw):
        p = r["product"]
        label = brands[p.brand_id].name if p.brand_id and p.brand_id in brands else "기타/미상"
        by_brand[label].append(r)

    out = []
    for label, rows in by_brand.items():
        prices = [r["current_price"] for r in rows]
        changes = [r["change_pct"] for r in rows if r["change_pct"] is not None]
        is_own = any(r["product"].is_own_brand for r in rows)
        out.append(
            {
                "brand": label,
                "brand_id": rows[0]["product"].brand_id,
                "is_own": is_own,
                "model_count": len(rows),
                "avg_price": round(statistics.mean(prices)),
                "min_price": min(prices),
                "median_change_pct": round(statistics.median(changes), 2) if changes else None,
            }
        )
    # 모델 수 많은 순(시장 존재감), 자사 우선
    out.sort(key=lambda r: (not r["is_own"], -r["model_count"]))
    return out


def data_quality(db: Session) -> dict:
    """데이터 신뢰성 투명성(QA A-1/A-2) — 실측 vs 합성 현황."""
    real_days = db.scalar(
        select(func.count(func.distinct(func.date(PriceSnapshot.collected_at)))).where(
            PriceSnapshot.is_synthetic.is_(False)
        )
    )
    synth_snaps = db.scalar(
        select(func.count()).select_from(PriceSnapshot).where(PriceSnapshot.is_synthetic.is_(True))
    )
    total_products = db.scalar(select(func.count()).select_from(Product))
    accessories = db.scalar(
        select(func.count()).select_from(Product).where(Product.is_accessory.is_(True))
    )
    rentals = db.scalar(
        select(func.count()).select_from(Product).where(Product.is_rental.is_(True))
    )
    # 합성 데이터 사용 여부(수요/환율)
    from app.models import DemandMetric, MacroMetric

    demand_synth = db.scalar(
        select(func.count()).select_from(DemandMetric).where(DemandMetric.source == "demo_synthetic")
    )
    macro_synth = db.scalar(
        select(func.count()).select_from(MacroMetric).where(MacroMetric.source == "demo_synthetic")
    )
    return {
        "real_collection_days": real_days or 0,
        "has_synthetic_price": (synth_snaps or 0) > 0,
        "synthetic_price_snapshots": synth_snaps or 0,
        "demand_is_synthetic": (demand_synth or 0) > 0,
        "macro_is_synthetic": (macro_synth or 0) > 0,
        "total_products": total_products or 0,
        "excluded_accessories": accessories or 0,
        "excluded_rentals": rentals or 0,
        "variation_ready": (real_days or 0) >= 2,
    }


def product_timeseries(db: Session, product_id: int) -> dict:
    """제품 시계열(F3)."""
    p = db.get(Product, product_id)
    if not p:
        return {}
    snaps = list(
        db.scalars(
            select(PriceSnapshot).where(PriceSnapshot.product_id == product_id)
        ).all()
    )
    daily = _daily_prices(snaps)
    series = [{"date": d.isoformat(), "price": daily[d]} for d in sorted(daily)]
    return {
        "product_id": p.id,
        "model_name": p.model_name,
        "is_own_brand": p.is_own_brand,
        "series": series,
    }


def _category_model_prices(db: Session) -> dict[int, list[dict]]:
    """카테고리별 (부품·렌탈·오배치 제외, 모델 dedup) 대표 제품 리스트."""
    products = _load_products(
        db, is_own_only=False, exclude_rental=True, exclude_accessory=True, exclude_offcat=True
    )
    snaps = _snaps_by_product(db, [p.id for p in products])
    raw: dict[int, list[dict]] = defaultdict(list)
    for p in products:
        ch = product_change(snaps.get(p.id, []))
        if ch["current_price"] is None:
            continue
        raw[p.category_id].append({"product": p, **ch})
    return {cid: _dedup_by_model(rows) for cid, rows in raw.items()}


def cuckoo_positioning(db: Session) -> list[dict]:
    """쿠쿠 포지셔닝(F-C): 카테고리별 쿠쿠 평균가 vs 카테고리 평균가 ±%.

    부품·렌탈 제외 + 모델 dedup 후 비교. (단, 용량/등급 미분리 — 참고용.
    동급 비교는 cuckoo_positioning_segmented 사용.)
    """
    cat_models = _category_model_prices(db)
    cats = {c.id: c.name for c in db.scalars(select(Category)).all()}

    results = []
    for cat_id, rows in cat_models.items():
        prices = [r["current_price"] for r in rows]
        own_prices = [r["current_price"] for r in rows if r["product"].is_own_brand]
        if not own_prices:
            continue
        own_avg = round(statistics.mean(own_prices))
        cat_avg = round(statistics.mean(prices))
        results.append(
            {
                "category_id": cat_id,
                "category_name": cats.get(cat_id, ""),
                "own_avg_price": own_avg,
                "category_avg_price": cat_avg,
                "own_min_price": min(own_prices),
                "positioning_pct": _change_pct(own_avg, cat_avg),
                "own_product_count": len(own_prices),
            }
        )
    results.sort(key=lambda r: r["category_name"])
    return results


def cuckoo_positioning_segmented(db: Session) -> list[dict]:
    """동급(용량 구간) 포지셔닝(B-1) — 같은 capacity_band 안에서만 쿠쿠 vs 시장 비교.

    예: 10인용 밥솥 쿠쿠 평균 vs 10인용 밥솥 시장 평균. like-for-like 의사결정용.
    """
    cat_models = _category_model_prices(db)
    cats = {c.id: c.name for c in db.scalars(select(Category)).all()}

    results = []
    for cat_id, rows in cat_models.items():
        # capacity_band 별로 분리
        bands: dict[str, list[dict]] = defaultdict(list)
        for r in rows:
            band = (r["product"].spec_json or {}).get("capacity_band")
            if band:
                bands[band].append(r)
        for band, brows in bands.items():
            own_prices = [r["current_price"] for r in brows if r["product"].is_own_brand]
            if not own_prices:
                continue
            all_prices = [r["current_price"] for r in brows]
            own_avg = round(statistics.mean(own_prices))
            seg_avg = round(statistics.mean(all_prices))
            results.append(
                {
                    "category_id": cat_id,
                    "category_name": cats.get(cat_id, ""),
                    "capacity_band": band,
                    "own_avg_price": own_avg,
                    "segment_avg_price": seg_avg,
                    "segment_size": len(all_prices),
                    "own_product_count": len(own_prices),
                    "positioning_pct": _change_pct(own_avg, seg_avg),
                }
            )
    results.sort(key=lambda r: (r["category_name"], r["capacity_band"]))
    return results
