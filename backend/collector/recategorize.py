"""데이터 기반 카테고리 자동 교정(오기입 점검·교정).

reclassify(카탈로그/코드 prefix/가스·전기 규칙) 다음에 실행되어, '네이버 상위분류
(category3)'를 권위 신호로 삼아 잘못 배치된 제품을 올바른 카테고리로 자동 이동한다.

원리 — 네이버 분류 ↔ 추적 카테고리 소유권(ownership):
  1) 각 추적 카테고리의 '대표 네이버분류'를 다수결로 구한다(표본 ≥5).
  2) 어떤 네이버분류가 '단 하나'의 카테고리에서만 대표면 그 카테고리가 소유자다.
     (여러 카테고리가 같은 네이버분류를 공유하면 모호 → 라우팅에 쓰지 않음)
  3) 제품의 네이버분류가 '다른 카테고리'에 소유돼 있고, 지금 카테고리에는 안 맞으면
     (지금 카테고리의 대표 네이버분류 ≠ 제품 네이버분류) → 소유 카테고리로 이동.

안전성:
  - 소유자가 유일한 경우만 이동(모호 분류는 손대지 않음).
  - 잡화(어느 카테고리도 대표가 아닌 네이버분류: 와인디캔터·양말 등)는 소유자가
    없어 이동되지 않고, 기존 off_category 규칙으로 가격 통계에서만 제외된다.
  - 카탈로그로 정배치된 제품은 네이버분류가 그 카테고리 대표와 일치 → 이동 대상 아님.

매 수집/배포마다 자동 실행(수기 점검 대체).

실행:  python -m collector.recategorize  (reclassify 직후)
"""
from __future__ import annotations

from collections import Counter, defaultdict

from sqlalchemy import select

from app.database import SessionLocal
from app.models import Category, Product

MIN_SAMPLE = 5  # 카테고리 대표 네이버분류 판정 최소 표본(aggregation과 동일)


def _build_authority(prods, cat_ids):
    """대표 네이버분류 + 유일소유자 맵을 만든다.

    반환: (dominant{cid->navercat}, owner{navercat->cid})
    """
    dist: dict[int, Counter] = defaultdict(Counter)
    for p in prods:
        if p.naver_cat:
            dist[p.category_id][p.naver_cat] += 1
    dominant = {
        cid: c.most_common(1)[0][0]
        for cid, c in dist.items()
        if sum(c.values()) >= MIN_SAMPLE
    }
    rev: dict[str, list[int]] = defaultdict(list)
    for cid, nc in dominant.items():
        rev[nc].append(cid)
    owner = {nc: cids[0] for nc, cids in rev.items() if len(cids) == 1}
    return dominant, owner


def recategorize() -> dict:
    db = SessionLocal()
    try:
        cat_names = {c.id: c.name for c in db.scalars(select(Category)).all()}
        cat_ids = set(cat_names)
        prods = db.scalars(
            select(Product).where(
                Product.is_rental.is_(False),
                Product.is_accessory.is_(False),
            )
        ).all()

        dominant, owner = _build_authority(prods, cat_ids)

        moves = 0
        by_move: Counter = Counter()
        examples: list[str] = []
        for p in prods:
            nc = p.naver_cat
            if not nc:
                continue
            tgt = owner.get(nc)
            if not tgt or tgt == p.category_id:
                continue
            # 지금 카테고리에 '맞으면'(대표분류와 일치) 이동하지 않음 — 정배치 보호
            if dominant.get(p.category_id) == nc:
                continue
            src_name = cat_names.get(p.category_id, "?")
            tgt_name = cat_names.get(tgt, "?")
            p.category_id = tgt
            moves += 1
            by_move[(src_name, tgt_name)] += 1
            if len(examples) < 12:
                examples.append(f"[{src_name}→{tgt_name}] {(p.model_name or '')[:46]}")
        db.commit()

        print(
            f"[recategorize] 본품 {len(prods)} | 소유권 매핑 {len(owner)} | 자동이동 {moves}"
        )
        for (src, tgt), n in by_move.most_common(20):
            print(f"  이동 {src} → {tgt}: {n}")
        for ex in examples:
            print(f"    예) {ex}")
        return {
            "checked": len(prods),
            "owner_maps": len(owner),
            "moves": moves,
            "by_move": {f"{s}→{t}": n for (s, t), n in by_move.items()},
            "examples": examples,
        }
    finally:
        db.close()


if __name__ == "__main__":
    import json

    print(json.dumps(recategorize(), ensure_ascii=False, indent=2))
