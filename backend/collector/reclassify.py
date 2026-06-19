"""기존 product에 개선된 매처를 재적용해 is_own_brand/brand_id 보정.

실행:  python -m collector.reclassify
(네이버 재수집 없이 DB의 brand_raw/model_name 기준으로 재분류)
"""
from __future__ import annotations

from sqlalchemy import select

from app.database import SessionLocal
from app.models import Category, Product
from app.spec import extract_spec
from app.textutil import (
    extract_model_key,
    is_accessory_title,
    is_rental_title,
    is_reseller_spam,
)
from collector.brand_matcher import BrandMatcher

# 가스 카테고리 검색이 '오븐레인지/레인지' 단어로 전기 제품을 끌어옴 →
# 제목에 '가스'가 없으면 전기 카운터파트로 이동(가스↔전기 분리).
_GAS_ROUTE = {
    "가스오븐레인지": "전자레인지·오븐",
    "가스레인지": "인덕션·전기레인지",
}
# 전기 제품 신호 — '가스'가 없고 이 중 하나라도 있으면 전기로 판단(가스 제품 오이동 방지)
_ELECTRIC_SIGNALS = ("전기", "전자", "광파", "복합", "인덕션", "에어프라이", "하이라이트")


def reclassify() -> dict:
    db = SessionLocal()
    try:
        matcher = BrandMatcher(db)
        cat_names = {c.id: c.name for c in db.scalars(select(Category)).all()}
        name_to_id = {n: i for i, n in cat_names.items()}
        products = list(db.scalars(select(Product)).all())

        before_own = sum(1 for p in products if p.is_own_brand)
        changed_to_own = 0
        changed_to_other = 0
        category_moves = 0
        promoted_examples: list[str] = []
        demoted_examples: list[str] = []

        for p in products:
            m = matcher.match(
                brand_raw=p.brand_raw or "",
                title=p.model_name or "",
                category_name=cat_names.get(p.category_id),
            )
            new_is_own = m.is_own
            if new_is_own != p.is_own_brand:
                if new_is_own:
                    changed_to_own += 1
                    if len(promoted_examples) < 5:
                        promoted_examples.append(p.model_name[:50])
                else:
                    changed_to_other += 1
                    if len(demoted_examples) < 8:
                        demoted_examples.append(p.model_name[:50])
            p.is_own_brand = new_is_own
            p.brand_id = m.brand_id
            p.is_rental = is_rental_title(p.model_name or "")
            # 별매품: 제목 신호 OR 공식 카탈로그 별매품 OR 리셀러 잡화(비교 제외)
            p.is_accessory = (
                is_accessory_title(p.model_name or "")
                or m.catalog_accessory
                or is_reseller_spam(p.model_name or "")
            )
            p.model_key = extract_model_key(p.model_name or "")
            # 카테고리 교정: 카탈로그(또는 카탈로그 기반 prefix 권위)가 카테고리를 주면 이동
            if m.catalog_category_id and m.catalog_category_id != p.category_id:
                category_moves += 1
                p.category_id = m.catalog_category_id
            # 폐지 카테고리 통합: 두피케어기 → 피부미용기(마사지·안마류는 안마의자·안마기)
            if cat_names.get(p.category_id) == "두피케어기":
                t = p.model_name or ""
                is_massage = ("마사지" in t) or ("안마" in t) or ("마사지" in (p.naver_cat or ""))
                target = name_to_id.get("안마의자·안마기" if is_massage else "피부미용기")
                if target:
                    category_moves += 1
                    p.category_id = target
            # 가스↔전기 라우팅: '가스' 카테고리에 들어온 전기 제품을 전기 카테고리로 이동.
            # (소비자 동질성 — 빌트인 가스 대형가전과 카운터탑 전기 소형가전을 섞지 않음)
            cur_cat = cat_names.get(p.category_id)
            if cur_cat in _GAS_ROUTE:
                nm = p.model_name or ""
                if "가스" not in nm and any(s in nm for s in _ELECTRIC_SIGNALS):
                    tid = name_to_id.get(_GAS_ROUTE[cur_cat])
                    if tid:
                        category_moves += 1
                        p.category_id = tid
            cap_val, cap_unit, band = extract_spec(
                cat_names.get(p.category_id), p.model_name or ""
            )
            p.capacity_value = cap_val
            p.capacity_unit = cap_unit
            p.spec_json = {"capacity_band": band} if band else None
        db.commit()

        after_own = sum(1 for p in products if p.is_own_brand)
        result = {
            "total_products": len(products),
            "own_before": before_own,
            "own_after": after_own,
            "newly_own": changed_to_own,
            "removed_false_positives": changed_to_other,
            "rental_total": sum(1 for p in products if p.is_rental),
            "accessory_total": sum(1 for p in products if p.is_accessory),
            "category_moves": category_moves,
            "with_model_key": sum(1 for p in products if p.model_key),
            "with_capacity": sum(1 for p in products if p.capacity_value),
            "demoted_examples": demoted_examples,
        }
        return result
    finally:
        db.close()


if __name__ == "__main__":
    import json

    res = reclassify()
    print(json.dumps(res, ensure_ascii=False, indent=2))
