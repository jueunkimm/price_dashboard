"""쿠쿠 모델코드 사전(방법 B) — 확인된 brand_raw=CUCKOO 제품에서 데이터 기반 추출 + 큐레이션.

각 모델코드 prefix가 등장해야 '타당한' 카테고리를 매핑한다. 짧은 prefix(AC/CP/CR/CF)는
카테고리 게이팅으로 오탐을 막는다(예: 'AC-...'는 공기청정기 카테고리에서만 쿠쿠로 인정).
실제 모델 리스트가 확보되면 이 사전을 확장/검수하면 된다.
"""
from __future__ import annotations

import re

# prefix → 인정 카테고리(소분류명) 집합
PREFIX_CATEGORIES: dict[str, set[str]] = {
    "CRP": {"전기밥솥"},
    "CR": {"전기밥솥"},
    "CHP": {"전기밥솥"},
    "CMC": {"멀티쿠커"},
    "CDW": {"식기세척기"},
    "CP": {"정수기"},
    "CPWP": {"정수기"},
    "CWP": {"정수기"},
    "AC": {"공기청정기"},
    "CMW": {"전자레인지·오븐"},
    "CIR": {"인덕션·전기레인지"},
    "CIH": {"인덕션·전기레인지"},
    "CAF": {"에어프라이어"},
    "CAFO": {"에어프라이어"},
    "CFM": {"믹서·블렌더"},
    "CVC": {"무선청소기"},
    "CKR": {"김치냉장고"},
    "CCM": {"커피머신"},
    "CBT": {"비데"},
    "CF": {"선풍기·서큘레이터"},
    "CHT": {"전기히터·온풍기"},
    "CMS": {"안마의자·안마기"},
}

# 모델코드 토큰: 알파벳 prefix + 하이픈 (CRP-EHB0310FW, AC-28..., CKR-ANLD...)
_CODE_TOKEN_RE = re.compile(r"\b([A-Z]{2,5})-[A-Z0-9]")


def cuckoo_code_in(title: str, category_name: str | None) -> str | None:
    """제목에 카테고리와 부합하는 쿠쿠 모델코드 prefix가 있으면 그 prefix 반환."""
    if not title:
        return None
    for m in _CODE_TOKEN_RE.finditer(title.upper()):
        pre = m.group(1)
        cats = PREFIX_CATEGORIES.get(pre)
        if cats and (category_name is None or category_name in cats):
            return pre
    return None
