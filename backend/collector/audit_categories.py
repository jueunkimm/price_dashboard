"""쿠쿠 제품 ↔ 카테고리 정합성 감사(QA 프로세스).

각 쿠쿠(is_own) 제품의 '권위 카테고리'와 실제 배치 카테고리를 비교해 불일치를 리포트한다.
권위 카테고리 = 공식 카탈로그(productlist.xlsx) 코드 매칭 > 카탈로그 기반 코드 prefix.
reclassify가 권위 카테고리로 이동시키므로 정상 상태면 불일치는 0에 수렴한다.
신규 수집에서 생긴 카테고리 오배치를 상시 점검하는 용도(비차단 — 리포트만).

실행:  python -m collector.audit_categories
"""
from __future__ import annotations

from collections import Counter

from sqlalchemy import select

from app import aggregation
from app.database import SessionLocal
from app.models import Category, Product
from collector.brand_matcher import BrandMatcher


def _audit_offcategory(db, cat_name: dict) -> dict:
    """전체 제품(브랜드 무관) 오배치 점검 — 네이버 상위분류(category3)가 카테고리
    대표와 다른 제품을 리포트. 가격 평균을 흐리는 오배치를 상시 감시한다."""
    dom = aggregation._category_dominant_navercat(db)
    prods = db.scalars(
        select(Product).where(
            Product.is_rental.is_(False), Product.is_accessory.is_(False)
        )
    ).all()
    off = [p for p in prods if aggregation.is_offcategory(p, dom)]
    by = Counter((cat_name.get(p.category_id, "?"), p.naver_cat) for p in off)
    print(f"[audit_offcategory] 전체 본품 {len(prods)} | 오배치(네이버분류 불일치) {len(off)}")
    for (cat, ncat), n in by.most_common(20):
        print(f"  오배치 {cat} ⟵ 네이버 '{ncat}': {n}")
    return {"checked": len(prods), "offcategory": len(off)}


def audit() -> dict:
    db = SessionLocal()
    try:
        m = BrandMatcher(db)
        cat_name = {c.id: c.name for c in db.scalars(select(Category)).all()}
        own = list(
            db.scalars(
                select(Product).where(
                    Product.is_own_brand.is_(True),
                    Product.is_accessory.is_(False),
                )
            ).all()
        )
        mismatches: list[tuple[str, str, str]] = []
        checked = 0
        for p in own:
            title = p.model_name or ""
            info = m._catalog_lookup(title)
            exp = info[0] if info else m._prefix_category_of(title)
            if not exp:
                continue  # 권위 카테고리를 알 수 없는 제품(카탈로그·prefix 미등록)
            checked += 1
            if exp != p.category_id:
                mismatches.append(
                    (cat_name.get(p.category_id, "?"), cat_name.get(exp, "?"), title[:50])
                )

        by = Counter((a, b) for a, b, _ in mismatches)
        print(
            f"[audit_categories] 쿠쿠 {len(own)} | 권위카테고리 확인가능 {checked} | "
            f"불일치 {len(mismatches)}"
        )
        for (act, exp), n in by.most_common(30):
            print(f"  불일치 {act} → {exp}: {n}")
        for act, exp, title in mismatches[:10]:
            print(f"    예) [{act}→{exp}] {title}")

        off = _audit_offcategory(db, cat_name)  # 전체 제품 오배치(네이버분류 기준)
        return {
            "own": len(own),
            "checked": checked,
            "mismatch": len(mismatches),
            **off,
        }
    finally:
        db.close()


if __name__ == "__main__":
    audit()
