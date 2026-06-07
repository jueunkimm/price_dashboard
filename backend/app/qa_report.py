"""자동 데이터 품질 리포트(QA) — 매 수집마다 생성, 대시보드에 노출.

수기 점검을 대체한다. 위험한 자동 변경(시드/카테고리 추가)은 하지 않고
'후보'만 탐지해 사람이 검토·결정하도록 한다.

  ① 시드 후보 브랜드 — 기타/미상 중 브랜드처럼 보이는 빈출 첫토큰(미시드)
  ② 신규 카테고리 후보 — 네이버 상위분류(category3)에 제품이 많은데 추적 안 하는 것
  ③ 오배치 요약 — 네이버 분류가 카테고리와 달라 가격을 흐리는 제품
"""
from __future__ import annotations

import re
from collections import Counter, defaultdict

from sqlalchemy import select

from app import aggregation
from app.models import Brand, Category, Product

# 브랜드가 아닌 일반어(첫 토큰 오탐 방지)
_NONBRAND = {
    "가정용", "업소용", "국산", "독일", "미니", "소형", "대용량", "정품", "무선",
    "휴대용", "신상", "신형", "최신", "초소형", "프리미엄", "고급", "스마트", "2025",
    "2026", "신제품", "특가", "할인", "당일발송", "무료배송",
}


def _norm(s: str) -> str:
    return (s or "").lower().replace(" ", "")


def _first_token(title: str) -> str:
    for tok in (title or "").split():
        if tok[:1] in "[(":
            continue
        return tok
    return ""


def build_qa_report(db) -> dict:
    products = list(
        db.scalars(
            select(Product).where(
                Product.is_accessory.is_(False), Product.is_rental.is_(False)
            )
        ).all()
    )
    cat_name = {c.id: c.name for c in db.scalars(select(Category)).all()}

    seeded: set[str] = set()
    for b in db.scalars(select(Brand)).all():
        for a in (b.aliases_json or []) + [b.name]:
            if a:
                seeded.add(_norm(a))

    # ① 시드 후보 브랜드
    tok_freq: Counter = Counter()
    tok_cats: dict[str, set] = defaultdict(set)
    for p in products:
        if p.brand_id is None:
            tok = _first_token(p.model_name or "")
            nt = _norm(tok)
            if (
                nt
                and nt not in seeded
                and 2 <= len(tok) <= 15
                and not tok.isdigit()
                and tok not in _NONBRAND
                and not re.match(r"^[A-Z]{2,5}-", tok)  # 모델코드 제외
            ):
                tok_freq[tok] += 1
                tok_cats[tok].add(cat_name.get(p.category_id))
    brand_candidates = [
        {"brand": t, "count": c, "categories": sorted(x for x in tok_cats[t] if x)[:3]}
        for t, c in tok_freq.most_common(25)
        if c >= 5
    ]

    # ② 신규 카테고리 후보 (네이버 category3 미추적)
    dom = aggregation._category_dominant_navercat(db)  # cat_id -> 대표 naver_cat
    covered = set(dom.values())
    nc_freq: Counter = Counter()
    nc_sample: dict[str, list] = defaultdict(list)
    for p in products:
        if p.naver_cat:
            nc_freq[p.naver_cat] += 1
            if len(nc_sample[p.naver_cat]) < 2:
                nc_sample[p.naver_cat].append((p.model_name or "")[:40])
    category_candidates = [
        {"naver_cat": nc, "count": c, "samples": nc_sample[nc]}
        for nc, c in nc_freq.most_common(40)
        if nc not in covered and c >= 20
    ]

    # ③ 오배치 요약
    off = [p for p in products if aggregation.is_offcategory(p, dom)]
    off_by = Counter((cat_name.get(p.category_id), p.naver_cat) for p in off)
    offcategory = [
        {"category": a, "naver_cat": b, "count": n}
        for (a, b), n in off_by.most_common(20)
    ]

    tot = len(products)
    unk_n = sum(1 for p in products if p.brand_id is None)
    return {
        "metrics": {
            "products": tot,
            "unknown_brand_pct": round(unk_n * 100 / tot) if tot else 0,
            "offcategory": len(off),
            "brand_candidates": len(brand_candidates),
            "category_candidates": len(category_candidates),
        },
        "brand_candidates": brand_candidates,
        "category_candidates": category_candidates,
        "offcategory": offcategory,
    }
