"""쿠쿠 모델 직접 수집(방법 B) — 공식 카탈로그 모델코드로 네이버를 직접 검색해
네이버 카테고리 검색에 안 잡힌 쿠쿠 모델까지 완전한 라인업 가격을 확보한다.

실행:  python -m collector.collect_cuckoo
- mapped_category 있고 별매품 아닌 카탈로그 모델만 대상.
- 모델코드 정확 매칭 결과만 채택(오매칭 방지). dedup: model_key=base_code.
"""
from __future__ import annotations

import time
from datetime import datetime, timezone

from sqlalchemy import select

from app.cuckoo_catalog import normalize_code
from app.database import Base, SessionLocal, engine
from app.models import Brand, Category, CollectionLog, CuckooModel, PriceSnapshot, Product
from app.spec import extract_spec
from app.textutil import extract_model_key
from collector.naver_client import NaverShopClient


def run_cuckoo_collection() -> dict:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    log = CollectionLog(status="running", message="cuckoo catalog")
    db.add(log)
    db.commit()

    own = db.scalar(select(Brand).where(Brand.is_own.is_(True)))
    targets = list(
        db.scalars(
            select(CuckooModel).where(
                CuckooModel.mapped_category_id.is_not(None),
                CuckooModel.is_accessory.is_(False),
            )
        ).all()
    )
    client = NaverShopClient()
    cats = {c.id: c.name for c in db.scalars(select(Category)).all()}

    found = notfound = snaps = created = 0
    try:
        for cm in targets:
            try:
                items = client.search(cm.base_code, display=5, sort="sim")
            except Exception as e:  # noqa: BLE001
                print(f"[cuckoo] '{cm.base_code}' 검색 실패: {e}")
                time.sleep(0.1)
                continue
            # 모델코드 정확 매칭 결과만 채택
            match = None
            for it in items:
                code = extract_model_key(it["title"])
                if code and normalize_code(code) == cm.base_code:
                    match = it
                    break
            if not match:
                notfound += 1
                time.sleep(0.05)
                continue

            prod = db.scalar(
                select(Product).where(
                    Product.model_key == cm.base_code, Product.is_own_brand.is_(True)
                )
            )
            if not prod:
                cap_v, cap_u, band = extract_spec(cats.get(cm.mapped_category_id), match["title"])
                prod = Product(
                    category_id=cm.mapped_category_id,
                    external_id=str(match["external_id"]) if match.get("external_id") else None,
                    model_name=match["title"],
                    brand_raw=match["brand_raw"] or None,
                    brand_id=own.id if own else None,
                    is_own_brand=True,
                    is_rental=False,
                    is_accessory=False,
                    model_key=cm.base_code,
                    capacity_value=cap_v,
                    capacity_unit=cap_u,
                    spec_json={"capacity_band": band} if band else None,
                )
                db.add(prod)
                db.flush()
                created += 1
            else:
                prod.category_id = cm.mapped_category_id  # 권위 카테고리

            db.add(
                PriceSnapshot(
                    product_id=prod.id,
                    channel="naver",
                    list_price=match["price"],
                    source=match["mall"] or None,
                    in_stock=True,
                )
            )
            snaps += 1
            found += 1
            if found % 50 == 0:
                db.commit()
                print(f"[cuckoo] 진행 {found}건 (신규 {created})")
            time.sleep(0.05)
        db.commit()
        log.status = "success"
    except Exception as e:  # noqa: BLE001
        db.rollback()
        log = db.get(CollectionLog, log.id)
        log.status = "error"
        log.message = str(e)
    finally:
        log.finished_at = datetime.now(timezone.utc)
        log.products_collected = found
        log.snapshots_inserted = snaps
        db.commit()
        db.close()
    result = {"targets": len(targets), "found": found, "new_products": created, "notfound": notfound}
    print(f"[cuckoo] 완료: {result}")
    return result


if __name__ == "__main__":
    import json

    print(json.dumps(run_cuckoo_collection(), ensure_ascii=False, indent=2))
