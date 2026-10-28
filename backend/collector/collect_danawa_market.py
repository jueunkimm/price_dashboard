"""Track A — 다나와 카테고리 기반 시장 전체 가격 수집 (재설계안 §3).

카테고리별 다나와 인기순 상위 N페이지의 카탈로그 상품(모델 단위·최저가)을 수집.
네이버 쇼핑 검색 API 종료(2026-07-31) 이후의 1차 가격 소스.

실행:  python -m collector.collect_danawa_market [--pages 3]
안정장치: 수집 0건 또는 성공 카테고리 절반 미만이면 exit 1 (빈 결과로 덮어쓰기 방지).
"""
from __future__ import annotations

import io
import json
import sys
from pathlib import Path

from sqlalchemy import select

from app.database import Base, SessionLocal, engine
from app.models import Category, CollectionLog, PriceSnapshot, Product
from app.spec import extract_spec
from app.textutil import extract_model_key, is_accessory_title, is_rental_title
from collector.brand_matcher import BrandMatcher
from collector.danawa_v2 import category_products

MAP_PATH = Path(__file__).resolve().parent.parent / "app" / "danawa_cate_map.json"
DEFAULT_PAGES = 3  # 페이지당 약 31개 → 카테고리당 최대 ~93개 모델


def _parse_pages(argv: list[str]) -> int:
    if "--pages" in argv:
        try:
            return max(1, int(argv[argv.index("--pages") + 1]))
        except (ValueError, IndexError):
            pass
    return DEFAULT_PAGES


def _upsert(db, category_id: int, category_name: str, it: dict, matcher: BrandMatcher) -> tuple[Product, bool]:
    """다나와 카탈로그 상품 upsert — external_id='danawa:{pcode}' 기준."""
    ext = f"danawa:{it['pcode']}"
    title = it["title"]
    # 제목에 모델코드가 없으면 보강(모델키 추출·검색성)
    mn = it.get("model_name_part") or ""
    if mn and mn.lower() not in title.lower():
        title = f"{title} {mn}"

    brand_raw = it.get("brand") or it.get("maker") or ""
    m = matcher.match(brand_raw=brand_raw, title=title, category_name=category_name, maker_raw=it.get("maker", ""))

    # 용량: 제목 + 다나와 스펙 문자열에서 추출(스펙이 더 정확)
    cap_val, cap_unit, band = extract_spec(category_name, f"{title} {it.get('spec_text', '')}")

    danawa_cat = (it.get("cate_names") or [None])[-1]
    spec_json = {
        k: v
        for k, v in {
            "capacity_band": band,
            "shop_count": it.get("shop_count"),
            "hit_rank": it.get("hit_rank"),
            "danawa_spec": (it.get("spec_text") or "")[:200] or None,
        }.items()
        if v
    }

    product = db.scalar(select(Product).where(Product.external_id == ext))
    created = False
    if not product:
        product = Product(
            category_id=category_id,
            external_id=ext,
            model_name=title[:300],
            brand_raw=brand_raw or None,
            brand_id=m.brand_id,
            is_own_brand=m.is_own,
            is_rental=is_rental_title(title),
            is_accessory=is_accessory_title(title),
            model_key=extract_model_key(title),
            naver_cat=(danawa_cat or "")[:60] or None,  # 분류 정합성 필드(다나와 분류명 재사용)
            image_url=(it.get("image") or "")[:500] or None,
            link=(it.get("url") or "")[:500] or None,
            capacity_value=cap_val,
            capacity_unit=cap_unit,
            spec_json=spec_json or None,
        )
        db.add(product)
        db.flush()
        created = True
    else:
        if m.brand_id and not product.brand_id:
            product.brand_id = m.brand_id
            product.is_own_brand = m.is_own
        if danawa_cat and product.naver_cat != danawa_cat[:60]:
            product.naver_cat = danawa_cat[:60]
        if it.get("image") and product.image_url != it["image"]:
            product.image_url = it["image"][:500]
        if it.get("url") and product.link != it["url"]:
            product.link = it["url"][:500]
        if cap_val and not product.capacity_value:
            product.capacity_value = cap_val
            product.capacity_unit = cap_unit
        merged = dict(product.spec_json or {})
        merged.update(spec_json)
        if merged != (product.spec_json or {}):
            product.spec_json = merged
    return product, created


def run(pages: int = DEFAULT_PAGES) -> dict:
    Base.metadata.create_all(bind=engine)
    if not MAP_PATH.exists():
        print("[danawa_market] 매핑 파일 없음 — collector.danawa_cate_map 먼저 실행")
        sys.exit(1)
    cate_map = json.loads(MAP_PATH.read_text(encoding="utf-8"))

    db = SessionLocal()
    log = CollectionLog(status="running")
    db.add(log)
    db.commit()

    products_n = snaps_n = cats_ok = cats_fail = 0
    try:
        matcher = BrandMatcher(db)
        name_to_cat = {c.name: c for c in db.scalars(select(Category).where(Category.level == 2)).all()}
        for name, info in cate_map.items():
            # 'cates'(복수) 지원 — 세탁기(드럼+통돌이)·냉장고(양문형+일반형)처럼
            # 다나와가 폼팩터로 분리한 카테고리는 여러 cate를 합산 수집
            cates = (info or {}).get("cates") or ([info["cate"]] if (info or {}).get("cate") else [])
            cat = name_to_cat.get(name)
            if not cates or not cat:
                continue
            try:
                got = 0
                for cate in cates:
                    for page in range(1, pages + 1):
                        items = category_products(cate, page=page)
                        if not items:
                            break
                        for it in items:
                            product, _ = _upsert(db, cat.id, name, it, matcher)
                            db.add(
                                PriceSnapshot(
                                    product_id=product.id,
                                    channel="danawa",
                                    list_price=it["price"],
                                    source="다나와 최저가",
                                )
                            )
                            snaps_n += 1
                            got += 1
                db.commit()
                products_n += got
                cats_ok += 1
                print(f"  ✓ {name}: {got}개 (cate={','.join(cates)})")
            except Exception as e:  # noqa: BLE001 — 카테고리 단위 격리
                db.rollback()
                cats_fail += 1
                print(f"  ✗ {name}: {e}")

        total_cates = cats_ok + cats_fail
        # 안정장치: 빈 수집/반토막 수집은 실패 처리 — 기존 데이터를 빈 결과로 덮지 않기 위함
        if products_n == 0 or (total_cates and cats_ok < total_cates * 0.5):
            log.status = "failed"
            log.message = f"danawa market 수집 가드 발동: ok={cats_ok}/{total_cates}, 제품 {products_n}"
            db.commit()
            print(f"[danawa_market] {log.message}")
            sys.exit(1)

        log.status = "success"
        log.categories_done = cats_ok
        log.products_collected = products_n
        log.snapshots_inserted = snaps_n
        log.message = "danawa market"
        db.commit()
        return {
            "categories_ok": cats_ok,
            "categories_fail": cats_fail,
            "products": products_n,
            "snapshots": snaps_n,
        }
    finally:
        db.close()


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    print(json.dumps(run(_parse_pages(sys.argv)), ensure_ascii=False, indent=2))
