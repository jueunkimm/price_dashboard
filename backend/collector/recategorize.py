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

from app.category_signals import route_target
from app.database import SessionLocal
from app.models import Category, Product
from collector.brand_matcher import BrandMatcher

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
        name_to_id = {n: i for i, n in cat_names.items()}
        cat_ids = set(cat_names)
        prods = db.scalars(
            select(Product).where(
                Product.is_rental.is_(False),
                Product.is_accessory.is_(False),
            )
        ).all()

        dominant, owner = _build_authority(prods, cat_ids)
        matcher = BrandMatcher(db)

        tracked = set(cat_names.values())
        moves = 0
        type_moves = 0
        code_moves = 0
        by_move: Counter = Counter()
        examples: list[str] = []
        for p in prods:
            src_name = cat_names.get(p.category_id, "?")
            # (0) 카탈로그 코드 권위 라우팅 — 쿠쿠 모델코드(CIR-/CRP- 등)가 가리키는
            #     공식 카테고리로 이동(예: '쿠쿠 요거트제조기' 결과의 쿠쿠 인덕션 CIR- → 인덕션·전기레인지)
            auth = matcher.authoritative_category(p.model_name or "")
            if auth and auth != p.category_id and auth in cat_names:
                tgt_name = cat_names[auth]
                p.category_id = auth
                moves += 1
                code_moves += 1
                by_move[(src_name, tgt_name)] += 1
                if len(examples) < 12:
                    examples.append(f"[코드][{src_name}→{tgt_name}] {(p.model_name or '')[:42]}")
                continue
            # (1) 제목 배타적 제품유형 라우팅 — 모델코드·naver_cat 없이도 명백한 오배치 교정
            #     (예: '쿠쿠 면도기' 보조검색에 섞인 쿠쿠 압력밥솥 → 전기밥솥)
            tname = route_target(p.model_name or "", src_name, tracked)
            if tname and tname != src_name:
                tid = name_to_id.get(tname)
                if tid:
                    p.category_id = tid
                    moves += 1
                    type_moves += 1
                    by_move[(src_name, tname)] += 1
                    if len(examples) < 12:
                        examples.append(f"[유형][{src_name}→{tname}] {(p.model_name or '')[:42]}")
                    continue
            # (2) 네이버분류 소유권 라우팅
            nc = p.naver_cat
            if not nc:
                continue
            tgt = owner.get(nc)
            if not tgt or tgt == p.category_id:
                continue
            # 지금 카테고리에 '맞으면'(대표분류와 일치) 이동하지 않음 — 정배치 보호
            if dominant.get(p.category_id) == nc:
                continue
            tgt_name = cat_names.get(tgt, "?")
            p.category_id = tgt
            moves += 1
            by_move[(src_name, tgt_name)] += 1
            if len(examples) < 12:
                examples.append(f"[분류][{src_name}→{tgt_name}] {(p.model_name or '')[:42]}")
        db.commit()

        print(
            f"[recategorize] 본품 {len(prods)} | 소유권 매핑 {len(owner)} | 자동이동 {moves}"
            f"(코드 {code_moves} + 제목유형 {type_moves} + 네이버분류 {moves - type_moves - code_moves})"
        )
        for (src, tgt), n in by_move.most_common(20):
            print(f"  이동 {src} → {tgt}: {n}")
        for ex in examples:
            print(f"    예) {ex}")
        return {
            "checked": len(prods),
            "owner_maps": len(owner),
            "moves": moves,
            "code_moves": code_moves,
            "type_moves": type_moves,
            "by_move": {f"{s}→{t}": n for (s, t), n in by_move.items()},
            "examples": examples,
        }
    finally:
        db.close()


if __name__ == "__main__":
    import json

    print(json.dumps(recategorize(), ensure_ascii=False, indent=2))
