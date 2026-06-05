"""경쟁사 핵심 모델 워치리스트(① 고정 추적셋).

네이버 카테고리 검색은 수집마다 상품이 바뀌어(churn) 경쟁사 모델의 가격 변동
이력이 끊긴다. 이를 보완해 '자사 경쟁 카테고리(★)'의 인기 경쟁모델을 모델코드로
매 수집 고정 조회해 연속 가격 이력을 확보한다. (자사 모델은 collect_cuckoo가 담당)

대상: 자사 본품이 있는 카테고리에서, 경쟁사 본품 중 리스팅 빈도(인기) 상위 모델.
기존 추적 제품의 스냅샷만 갱신(신규 생성은 일반 수집에 위임).

실행:  python -m collector.collect_watchlist
"""
from __future__ import annotations

import time
from collections import Counter, defaultdict

from sqlalchemy import select

from app.cuckoo_catalog import normalize_code
from app.database import SessionLocal
from app.models import PriceSnapshot, Product
from app.textutil import extract_model_key
from collector.naver_client import NaverShopClient

TOP_N_PER_CAT = 12  # 카테고리별 추적할 경쟁 모델 수


def run_watchlist(top_n: int = TOP_N_PER_CAT) -> dict:
    db = SessionLocal()
    try:
        own_cats = set(
            db.scalars(
                select(Product.category_id).where(
                    Product.is_own_brand.is_(True), Product.is_accessory.is_(False)
                ).distinct()
            ).all()
        )
        rivals = db.scalars(
            select(Product).where(
                Product.is_own_brand.is_(False),
                Product.is_accessory.is_(False),
                Product.is_rental.is_(False),
                Product.model_key.is_not(None),
            )
        ).all()
        # 카테고리별 모델키 빈도(인기) → 상위 N
        freq: dict[int, Counter] = defaultdict(Counter)
        for p in rivals:
            if p.category_id in own_cats:
                freq[p.category_id][p.model_key] += 1
        watch: list[str] = []
        for _cat, cc in freq.items():
            watch += [mk for mk, _ in cc.most_common(top_n)]
        watch = list(dict.fromkeys(watch))  # dedup

        client = NaverShopClient()
        snaps = updated = 0
        for mk in watch:
            try:
                items = client.search(mk, display=5)
            except Exception:  # noqa: BLE001
                time.sleep(0.05)
                continue
            match = None
            for it in items:
                c = extract_model_key(it["title"])
                if c and normalize_code(c) == normalize_code(mk):
                    match = it
                    break
            if not match:
                time.sleep(0.05)
                continue
            prod = None
            if match.get("external_id"):
                prod = db.scalar(
                    select(Product).where(Product.external_id == str(match["external_id"]))
                )
            if not prod:
                prod = db.scalar(
                    select(Product).where(
                        Product.model_key == mk, Product.is_own_brand.is_(False)
                    )
                )
            if not prod:
                time.sleep(0.05)
                continue  # 신규 생성은 일반 수집에 위임 — 기존 추적 대상만 연속 갱신
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
            updated += 1
            if snaps % 50 == 0:
                db.commit()
            time.sleep(0.1)
        db.commit()
        print(f"[watchlist] 경쟁 워치 모델 {len(watch)} | 갱신 {updated} 스냅샷 {snaps}")
        return {"watch": len(watch), "snapshots": snaps}
    finally:
        db.close()


if __name__ == "__main__":
    run_watchlist()
