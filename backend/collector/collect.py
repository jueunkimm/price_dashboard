"""수집 잡(F6) — 카테고리별 네이버쇼핑 가격을 price_snapshot에 적재.

실행:  python -m collector.collect
- 카테고리(level=2)를 순회하며 검색 → 브랜드 매칭 → product upsert → snapshot insert
- 실행 결과를 collection_log에 기록
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select

from app.config import settings
from app.database import Base, SessionLocal, engine
from app.models import Category, CollectionLog, PriceSnapshot, Product
from app.spec import extract_spec
from app.textutil import extract_model_key, is_accessory_title, is_rental_title
from collector.brand_matcher import BrandMatcher
from collector.naver_client import NaverShopClient


def _upsert_product(
    db, category_id: int, item: dict, matcher: BrandMatcher, category_name: str | None = None
) -> Product:
    """external_id(없으면 model_name) 기준 product upsert + 브랜드 매칭."""
    m = matcher.match(
        brand_raw=item["brand_raw"],
        title=item["title"],
        category_name=category_name,
        maker_raw=item.get("maker_raw", ""),
    )

    product = None
    if item.get("external_id"):
        product = db.scalar(
            select(Product).where(Product.external_id == str(item["external_id"]))
        )
    if not product:
        cap_val, cap_unit, band = extract_spec(category_name, item["title"])
        product = Product(
            category_id=category_id,
            external_id=str(item["external_id"]) if item.get("external_id") else None,
            model_name=item["title"],
            brand_raw=item["brand_raw"] or None,
            brand_id=m.brand_id,
            is_own_brand=m.is_own,
            is_rental=is_rental_title(item["title"]),
            is_accessory=is_accessory_title(item["title"]),
            model_key=extract_model_key(item["title"]),
            sub_category=(item.get("sub_category") or "")[:60] or None,
            capacity_value=cap_val,
            capacity_unit=cap_unit,
            spec_json={"capacity_band": band} if band else None,
        )
        db.add(product)
        db.flush()
    else:
        # 매칭 정보가 새로 생기면 갱신(검수 루프 보강)
        if m.brand_id and not product.brand_id:
            product.brand_id = m.brand_id
            product.is_own_brand = m.is_own
        # 세부분류(category4)는 기존 제품에도 backfill — 첫 수집 후 일괄 채워짐
        sub = (item.get("sub_category") or "")[:60] or None
        if sub and product.sub_category != sub:
            product.sub_category = sub
    return product


def run_collection(display: int | None = None) -> dict:
    Base.metadata.create_all(bind=engine)
    display = display or settings.collect_display
    db = SessionLocal()
    log = CollectionLog(status="running")
    db.add(log)
    db.commit()

    products_collected = 0
    snapshots_inserted = 0
    categories_done = 0
    try:
        client = NaverShopClient()
        matcher = BrandMatcher(db)
        categories = list(
            db.scalars(select(Category).where(Category.level == 2)).all()
        )
        for cat in categories:
            keyword = cat.search_keyword or cat.name
            try:
                items = client.search(keyword, display=display)
            except Exception as e:  # noqa: BLE001 — 한 카테고리 실패가 전체를 막지 않도록
                print(f"[collect] '{keyword}' 검색 실패: {e}")
                continue

            # 자사 보조 검색 — 일반 검색 상위 N위 밖이라도 쿠쿠 제품을 반드시 포착
            # (틈새 카테고리에서 자사 누락·★ 미표시 방지). external_id로 중복 제거.
            # 단, '쿠쿠 X' 검색은 관련도 노이즈(리셀러 쿠쿠스토어 등)를 포함하므로
            # '진짜 쿠쿠'(카탈로그/정확 brand·maker)만 채택해 카테고리 오염을 막는다.
            try:
                own_hits = [
                    it for it in client.search(f"쿠쿠 {keyword}", display=20)
                    if matcher.is_strong_own(it.get("brand_raw", ""), it["title"], it.get("maker_raw", ""))
                ]
                items = items + own_hits
            except Exception as e:  # noqa: BLE001
                print(f"[collect] 'cuckoo {keyword}' 보조검색 실패: {e}")
            seen_ids: set[str] = set()
            deduped = []
            for it in items:
                eid = str(it.get("external_id") or "")
                if eid and eid in seen_ids:
                    continue
                if eid:
                    seen_ids.add(eid)
                deduped.append(it)
            items = deduped

            for item in items:
                product = _upsert_product(db, cat.id, item, matcher, category_name=cat.name)
                products_collected += 1
                db.add(
                    PriceSnapshot(
                        product_id=product.id,
                        channel="naver",
                        list_price=item["price"],
                        source=item["mall"] or None,
                        in_stock=True,
                    )
                )
                snapshots_inserted += 1
            db.commit()
            categories_done += 1
            print(f"[collect] {cat.name}: {len(items)}건")

        log.status = "success"
        log.message = "ok"
    except Exception as e:  # noqa: BLE001
        db.rollback()
        log = db.get(CollectionLog, log.id)
        log.status = "error"
        log.message = str(e)
        print(f"[collect] 실패: {e}")
    finally:
        log.finished_at = datetime.now(timezone.utc)
        log.categories_done = categories_done
        log.products_collected = products_collected
        log.snapshots_inserted = snapshots_inserted
        db.commit()
        result = {
            "status": log.status,
            "categories_done": categories_done,
            "products_collected": products_collected,
            "snapshots_inserted": snapshots_inserted,
        }
        db.close()
    print(f"[collect] 완료: {result}")
    return result


if __name__ == "__main__":
    run_collection()
