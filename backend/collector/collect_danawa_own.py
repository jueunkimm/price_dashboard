"""Track B — 쿠쿠 카탈로그 모델 전수 다나와 트래킹 (재설계안 §3).

productlist.xlsx(CuckooModel)의 본품 모델코드를 다나와 통합검색으로 조회해
모델별 최저가를 수집한다. 카탈로그(가격비교) 항목 우선, 없으면 몰 오퍼 최저가 폴백.

실행:  python -m collector.collect_danawa_own [--max 900]
안정장치: 발견 모델 0건이면 exit 1.
"""
from __future__ import annotations

import io
import json
import re
import sys

from sqlalchemy import select

from app.database import Base, SessionLocal, engine
from app.models import CollectionLog, CuckooModel, PriceSnapshot, Product
from app.textutil import is_accessory_title, is_rental_title
from collector.brand_matcher import BrandMatcher
from collector.collect_danawa_market import _upsert
from collector.danawa_v2 import search_offers, search_products


def _parse_max(argv: list[str]) -> int:
    if "--max" in argv:
        try:
            return max(1, int(argv[argv.index("--max") + 1]))
        except (ValueError, IndexError):
            pass
    return 900


def _norm(s: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", (s or "").upper())


def _pick_catalog(code: str, items: list[dict]) -> dict | None:
    """검색 카탈로그 항목에서 본품 1개 선택 — 코드 포함·비부품·비렌탈, 쿠쿠 우선, 최고가(부품 배제)."""
    nc = _norm(code)
    cands = [
        it
        for it in items
        # 정식 카탈로그(숫자 pcode)만 — 몰 리스팅(EE128_… 코드)은 상세 페이지가 없어
        # 링크가 깨지고 단일 몰 가격이라 최저가도 아니다. 몰 단위는 오퍼 폴백이 담당.
        if it.get("is_catalog", True)
        and nc and nc in _norm(it["title"])
        and not is_accessory_title(it["title"])
        and not is_rental_title(it["title"])
    ]
    cuckoo = [it for it in cands if "쿠쿠" in (it.get("maker") or "") or "쿠쿠" in it["title"]]
    pool = cuckoo or cands
    return max(pool, key=lambda x: x["price"]) if pool else None


def purge_broken_mall_products(db) -> int:
    """몰 상품코드(EE128_… 등)로 잘못 만들어진 제품과 그 이력을 정리한다.

    이전 버전은 몰 리스팅을 카탈로그 상품으로 착각해 external_id를 'danawa:EE128_3964263358'
    꼴로 저장했고, 링크(info?pcode=몰코드)가 열리지 않았다. 이들은 정식 카탈로그 항목(또는
    'danawa:offer-코드')으로 대체되므로 중복 방지를 위해 제거한다. 멱등 — 없으면 0건.
    """
    from sqlalchemy import delete, update

    from app.models import Alert

    ids = [
        pid
        for pid, ext in db.execute(
            select(Product.id, Product.external_id).where(Product.external_id.like("danawa:%"))
        ).all()
        if ext and not ext[len("danawa:"):].isdigit() and not ext.startswith("danawa:offer-")
    ]
    if not ids:
        return 0
    for i in range(0, len(ids), 500):  # SQLite 변수 한도 대비 청크
        chunk = ids[i : i + 500]
        db.execute(update(Alert).where(Alert.product_id.in_(chunk)).values(product_id=None))
        db.execute(delete(PriceSnapshot).where(PriceSnapshot.product_id.in_(chunk)))
        db.execute(delete(Product).where(Product.id.in_(chunk)))
    db.commit()
    return len(ids)


def run(max_models: int = 900) -> dict:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    purged = purge_broken_mall_products(db)
    if purged:
        print(f"[danawa_own] 깨진 몰코드 제품 {purged}개 정리(정식 카탈로그/오퍼로 대체)")
    log = CollectionLog(status="running")
    db.add(log)
    db.commit()

    found = missed = snaps = 0
    try:
        matcher = BrandMatcher(db)
        models = list(
            db.scalars(
                select(CuckooModel)
                .where(CuckooModel.is_accessory.is_(False), CuckooModel.mapped_category_id.is_not(None))
                .order_by(CuckooModel.base_code)
            ).all()
        )
        # base_code 단위 dedup
        seen: set[str] = set()
        targets = []
        for m in models:
            if m.base_code in seen:
                continue
            seen.add(m.base_code)
            targets.append(m)
        targets = targets[:max_models]

        cat_names = {}  # category_id -> name 캐시
        from app.models import Category

        for c in db.scalars(select(Category)).all():
            cat_names[c.id] = c.name

        for i, m in enumerate(targets, 1):
            code = m.base_code
            cat_id = m.mapped_category_id
            cat_name = cat_names.get(cat_id, "")
            try:
                best = _pick_catalog(code, search_products(code))
                if best:
                    it = {**best, "model_name_part": code, "cate_names": [], "shop_count": None, "hit_rank": None, "image": None}
                    product, _ = _upsert(db, cat_id, cat_name, it, matcher)
                    db.add(
                        PriceSnapshot(
                            product_id=product.id,
                            channel="danawa",
                            list_price=best["price"],
                            source="다나와 최저가",
                        )
                    )
                    snaps += 1
                    found += 1
                else:
                    # 폴백: 몰 오퍼 최저가 (카탈로그 미등록 모델)
                    nc = _norm(code)
                    offers = [
                        o
                        for o in search_offers(code)
                        if nc in _norm(o.get("name") or "")
                        and not is_accessory_title(o["name"])
                        and not is_rental_title(o["name"])
                    ]
                    if offers:
                        o = min(offers, key=lambda x: x["price"])
                        it = {
                            "pcode": f"offer-{code}",
                            "title": o["name"],
                            "model_name_part": code,
                            "maker": "쿠쿠",
                            "brand": "쿠쿠",
                            "price": o["price"],
                            "spec_text": "",
                            "cate_names": [],
                            "shop_count": None,
                            "hit_rank": None,
                            "image": None,
                            "url": o.get("link"),
                        }
                        product, _ = _upsert(db, cat_id, cat_name, it, matcher)
                        db.add(
                            PriceSnapshot(
                                product_id=product.id,
                                channel="danawa",
                                list_price=o["price"],
                                source="다나와 오퍼",
                            )
                        )
                        snaps += 1
                        found += 1
                    else:
                        missed += 1
                if i % 50 == 0:
                    db.commit()
                    print(f"  … {i}/{len(targets)} (발견 {found})")
            except Exception as e:  # noqa: BLE001 — 모델 단위 격리
                db.rollback()
                missed += 1
                print(f"  ✗ {code}: {e}")
        db.commit()

        if found == 0:
            log.status = "failed"
            log.message = f"danawa own 수집 가드 발동: 발견 0 / 대상 {len(targets)}"
            db.commit()
            print(f"[danawa_own] {log.message}")
            sys.exit(1)

        log.status = "success"
        log.categories_done = 0
        log.products_collected = found
        log.snapshots_inserted = snaps
        log.message = "danawa own(cuckoo catalog)"
        db.commit()
        return {"targets": len(targets), "found": found, "missed": missed, "snapshots": snaps}
    finally:
        db.close()


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    print(json.dumps(run(_parse_max(sys.argv)), ensure_ascii=False, indent=2))
