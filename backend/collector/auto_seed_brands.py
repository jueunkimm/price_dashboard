"""고신뢰 브랜드 자동 시드 — 기타/미상 중 '여러 카테고리에 걸친 빈출 브랜드명'을
자동으로 brand 테이블에 등록(is_own=False). 이후 reclassify가 매칭한다.

안전 기준(오탐 최소화):
  - 교차 카테고리(≥2): 진짜 브랜드는 여러 품목에 걸침. 제품유형어(계란찜기 등)는 단일 카테고리.
  - 빈도(≥6): 일회성 노이즈 배제.
  - 노이즈 필터: 모델코드/숫자시작(스펙)/리셀러(스토어)/일반어 제외.
단일 카테고리·애매한 후보는 자동 시드하지 않고 QA 패널에서 사람이 검토한다.

실행:  python -m collector.auto_seed_brands  (reclassify 직전)
"""
from __future__ import annotations

import re
from collections import Counter, defaultdict

from sqlalchemy import select

from app.database import SessionLocal
from app.models import Brand, Product
from app.qa_report import _NONBRAND, _first_token, _norm

MIN_COUNT = 6
MIN_CATEGORIES = 2  # 교차 카테고리 = 브랜드 신호

# 자동 시드에서 추가로 막을 제품유형/설명어(교차 카테고리로 새어도 차단)
_EXTRA_BLOCK = {
    "계란찜기", "라면포트", "전기포트", "다용도", "만능", "이동식", "벽걸이",
    "스탠드", "원룸", "주방", "가정", "사무실", "여행용", "충전식", "접이식",
    "초경량", "무소음", "저소음", "강력", "정품", "차량용", "휴대", "탁상용",
    "대형", "특대형", "초소형", "자동", "수동", "1인용", "2인용", "신상품",
}


def _is_descriptor(tok: str) -> bool:
    """제품 설명어 패턴(브랜드 아님): '~용'(여행용)·'~식'(충전식)으로 끝나는 일반어."""
    return tok.endswith("용") or tok.endswith("식")


def run_auto_seed() -> dict:
    db = SessionLocal()
    try:
        seeded: set[str] = set()
        for b in db.scalars(select(Brand)).all():
            for a in (b.aliases_json or []) + [b.name]:
                if a:
                    seeded.add(_norm(a))

        unk = db.scalars(
            select(Product).where(
                Product.brand_id.is_(None),
                Product.is_accessory.is_(False),
                Product.is_rental.is_(False),
            )
        ).all()
        freq: Counter = Counter()
        cats: dict[str, set] = defaultdict(set)
        for p in unk:
            tok = _first_token(p.model_name or "")
            nt = _norm(tok)
            if (
                nt
                and nt not in seeded
                and 2 <= len(tok) <= 15
                and not tok.isdigit()
                and tok not in _NONBRAND
                and tok not in _EXTRA_BLOCK
                and not _is_descriptor(tok)
                and not re.match(r"^[A-Z]{2,5}-", tok)
                and not re.match(r"^\d", tok)
                and not re.search(r"(스토어|마켓|샵)$", tok)
            ):
                freq[tok] += 1
                cats[tok].add(p.category_id)

        added: list[str] = []
        for tok, c in freq.items():
            if c >= MIN_COUNT and len(cats[tok]) >= MIN_CATEGORIES:
                if not db.scalar(select(Brand).where(Brand.name == tok)):
                    db.add(Brand(name=tok, is_own=False, aliases_json=[tok]))
                    added.append(tok)
        db.commit()
        print(f"[auto_seed_brands] 고신뢰 브랜드 {len(added)}개 자동 시드: {added}")
        return {"added": added}
    finally:
        db.close()


if __name__ == "__main__":
    run_auto_seed()
