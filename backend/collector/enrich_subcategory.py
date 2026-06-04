"""세부유형(category4) 보강 — 미분류(null) 상품을 실제 세부유형으로 편입.

원인: 카테고리 키워드 검색 시 개별 판매 리스팅은 네이버 category4가 없어
sub_category=null("미분류")로 남는다. 두 방법으로 편입한다.

- 방법 A(제목 키워드): 제목에 강한 유형 신호(압력·드럼·냉온 등)가 있으면 즉시 분류(API 0).
- 방법 C(모델코드 재조회): 남은 null을 모델코드로 네이버 재검색 → 카탈로그 category4 차용.
  카테고리 키워드 검색과 달리 모델코드 검색은 카탈로그 상품과 매칭돼 공식 분류가 나온다.

정확도 검증(실데이터): 방법 C ~100%(네이버 공식분류), 방법 A 85~100%.
비용: 고유 모델코드당 1콜(약 300여 콜, 네이버 일일한도의 ~1.3%). 한 번 채우면 저장되어
이후 수집에선 신규 null만 소량 재조회.

실행:  python -m collector.enrich_subcategory
"""
from __future__ import annotations

import re
import time
from collections import Counter, defaultdict

from sqlalchemy import select

from app.database import SessionLocal
from app.models import Category, Product
from collector.naver_client import NaverShopClient

# 방법 A: 카테고리별 (세부유형 라벨, [제목 키워드]) — 오탐 방지 위해 강한 신호만.
# 라벨은 실제 네이버 category4 값과 동일해야 기존 세부유형과 합쳐진다.
TITLE_RULES: dict[str, list[tuple[str, list[str]]]] = {
    "전기밥솥": [("압력밥솥", ["압력"]), ("업소용밥솥", ["업소용"])],
    "정수기": [("냉온정수기", ["냉온", "냉/온"]), ("무전원정수기", ["무전원", "직수형"])],
    "세탁기": [("드럼세탁기", ["드럼"]), ("세탁기+건조기 세트", ["세탁기+건조기", "세탁건조기세트"])],
    "냉장고": [("양문형냉장고", ["양문"]), ("업소용냉장고", ["업소용"])],
    "가습기": [("초음파식가습기", ["초음파"]), ("가열식가습기", ["가열식"])],
    "김치냉장고": [("스탠드형", ["스탠드"]), ("뚜껑형", ["뚜껑"])],
}

# 모델코드 토큰(예: CRP-AHF1010, CWM-ATFF1210B, WP-N01WH).
# 하이픈 필수 + 접미부에 숫자 1개 이상 — 'CUCKOO' 같은 브랜드어 오매칭 방지.
_CODE_RE = re.compile(r"[A-Z]{2,5}-[A-Z]*\d[A-Z0-9]*")


def _norm(s: str) -> str:
    return (s or "").upper().replace("-", "").replace(" ", "")


def _title_subtype(cat_name: str | None, title: str | None) -> str | None:
    """방법 A — 제목에 강한 유형 신호가 있으면 해당 세부유형 라벨."""
    t = title or ""
    for label, kws in TITLE_RULES.get(cat_name or "", []):
        if any(k in t for k in kws):
            return label
    return None


def _model_code(title: str | None) -> str | None:
    m = _CODE_RE.search((title or "").upper())
    return m.group(0) if m else None


def _resolve_subtype(items: list[dict], code: str) -> str | None:
    """방법 C 핵심 — 재조회 결과에서 모델코드가 제목에 든 항목의 category4 다수결.

    모델코드가 제목에 실제로 포함된 항목만 신뢰해 코드 충돌 오탐을 막는다.
    """
    ncode = _norm(code)
    found = [
        it["sub_category"]
        for it in items
        if it.get("sub_category") and ncode in _norm(it.get("title"))
    ]
    return Counter(found).most_common(1)[0][0] if found else None


def display_subtype(
    category_name: str | None, title: str | None, dist: "Counter | None"
) -> str | None:
    """미분류(null) 상품의 표시용 세부유형 폴백(API 없음, export 시점).

    우선순위: 제목 키워드(정확) → 단일유형 카테고리(그 유형 하나뿐, 정확)
    → 다중유형이면 최빈 유형(차선 추정). dist는 해당 카테고리의 non-null 세부유형 빈도.
    네이버가 세분류를 안 하는 카테고리(dist 비어있음)는 None 유지.
    """
    st = _title_subtype(category_name, title)
    if st:
        return st
    if not dist:
        return None
    labels = list(dist)
    if len(labels) == 1:
        return labels[0]  # 단일유형 → 정확
    return dist.most_common(1)[0][0]  # 다중유형 → 최빈(차선)


def enrich(max_codes: int = 800, sleep: float = 0.15) -> dict:
    db = SessionLocal()
    a_count = 0
    c_count = 0
    calls = 0
    try:
        cats = {c.id: c.name for c in db.scalars(select(Category)).all()}
        nulls = list(
            db.scalars(
                select(Product).where(
                    Product.sub_category.is_(None),
                    Product.is_accessory.is_(False),
                )
            ).all()
        )

        # 방법 A 먼저(무료) — 제목 신호로 분류
        for p in nulls:
            st = _title_subtype(cats.get(p.category_id), p.model_name)
            if st:
                p.sub_category = st[:60]
                a_count += 1
        db.commit()

        # 방법 C — 남은 null을 고유 모델코드로 묶어 재조회
        by_code: dict[str, list[Product]] = defaultdict(list)
        for p in nulls:
            if p.sub_category:
                continue
            code = _model_code(p.model_name)
            if code:
                by_code[code].append(p)

        client = NaverShopClient()
        for code, prods in list(by_code.items())[:max_codes]:
            try:
                items = client.search(code, display=5)
            except Exception as e:  # noqa: BLE001 — 한 건 실패가 전체를 막지 않게
                print(f"[enrich] '{code}' 재조회 실패: {e}")
                continue
            calls += 1
            best = _resolve_subtype(items, code)
            if best:
                for p in prods:
                    p.sub_category = best[:60]
                    c_count += 1
            if calls % 50 == 0:
                db.commit()
            time.sleep(sleep)
        db.commit()
        print(
            f"[enrich_subcategory] 방법A {a_count}건 / 방법C {c_count}건"
            f"(재조회 {calls}콜) 세부유형 편입"
        )
        return {"method_a": a_count, "method_c": c_count, "calls": calls}
    finally:
        db.close()


if __name__ == "__main__":
    enrich()
