"""카테고리별 규격(스펙) 축 정의 — 정밀도 고도화.

핵심: 카테고리마다 '의미 있는 규격 단위'가 다르다. 그 카테고리에 맞는 단위만
추출해야 오인식(예: 밥솥의 '1.8L 내솥'을 냉장고급 L로 처리)을 막고 동급 비교가 정확해진다.

각 단위: (정규식, 밴드 라벨 함수). extract_spec(category_name, title)이
해당 카테고리의 단위들을 우선순위대로 시도해 (값, 단위, 밴드)를 반환.
"""
from __future__ import annotations

import re

# ── 단위별 정규식 + 밴드(동급 비교용 구간) ──
_PATTERNS: dict[str, re.Pattern] = {
    "인용": re.compile(r"(\d+)\s*인용?(?!치)"),
    "kg": re.compile(r"(\d+(?:\.\d+)?)\s*kg", re.IGNORECASE),
    "형": re.compile(r"(\d{2,3})\s*(?:형|인치)"),
    "평": re.compile(r"(\d+)\s*평"),
    "L": re.compile(r"(\d+(?:\.\d+)?)\s*[lL리터]"),
    "구": re.compile(r"(\d)\s*구"),
    "bar": re.compile(r"(\d{1,2})\s*(?:bar|바|기압)", re.IGNORECASE),
    "ch": re.compile(r"(\d(?:\.\d)?)\s*(?:ch|채널)", re.IGNORECASE),
    "W": re.compile(r"(\d{3,4})\s*w(?:att)?", re.IGNORECASE),
}


def band_for(value: float | None, unit: str | None) -> str | None:
    """저장된 (값, 단위)로부터 밴드 라벨 재계산. 집계에서 사용."""
    if value is None or unit is None or unit not in _PATTERNS:
        return None
    return _band(value, unit)


def _band(value: float, unit: str) -> str:
    if unit == "인용":
        return f"{int(value)}인용"
    if unit == "kg":
        return f"{int(value)}kg"
    if unit == "형":
        return f"{int(value)}형"
    if unit == "구":
        return f"{int(value)}구"
    if unit == "ch":
        return f"{value}채널"
    if unit == "bar":
        return f"{int(value)}Bar"
    if unit == "W":
        lo = int(value // 500) * 500
        return f"{lo}~{lo + 500}W"
    if unit == "평":
        lo = (int(value) // 10) * 10
        return f"{lo}~{lo + 10}평"
    if unit == "L":
        lo = int(value // 5) * 5
        return f"{lo}~{lo + 5}L"
    return str(value)


# ── 카테고리 → 규격 단위(우선순위) ──
# 표준 수치 규격이 없는 카테고리(타입·기능 위주)는 빈 리스트.
CATEGORY_SPEC: dict[str, list[str]] = {
    "전기밥솥": ["인용"],
    "식기세척기": ["인용"],
    "멀티쿠커": ["L", "인용"],
    "냉장고": ["L"],
    "김치냉장고": ["L"],
    "전자레인지·오븐": ["L"],
    "에어프라이어": ["L"],
    "믹서·블렌더": ["L"],
    "정수기": [],  # 직수/저수조 — 표준 수치 규격 아님
    "커피머신": ["bar"],
    "인덕션·전기레인지": ["구"],
    "세탁기": ["kg"],
    "건조기": ["kg"],
    "의류관리기": ["kg"],
    "무선청소기": ["W"],
    "로봇청소기": [],
    "스팀다리미": ["W"],
    "비데": [],
    "에어컨": ["평"],
    "선풍기·서큘레이터": [],
    "제습기": ["L"],
    "가습기": ["L"],
    "공기청정기": ["평"],
    "전기히터·온풍기": ["W"],
    "TV": ["형"],
    "사운드바": ["ch"],
    "프로젝터": [],
    "헤어드라이어·스타일러": ["W"],
    "면도기": [],
    "안마의자·안마기": [],
    "체중계": [],
}


def extract_spec(
    category_name: str | None, title: str
) -> tuple[float | None, str | None, str | None]:
    """(값, 단위, 밴드) 반환. 카테고리에 정의된 단위만 우선순위대로 시도.

    category_name 미지정 시 전 단위를 일반 우선순위로 시도(하위호환).
    """
    if not title:
        return None, None, None
    units = (
        CATEGORY_SPEC.get(category_name)
        if category_name is not None
        else ["인용", "kg", "형", "평", "L"]
    )
    if not units:
        return None, None, None
    for unit in units:
        m = _PATTERNS[unit].search(title)
        if m:
            val = float(m.group(1))
            return val, unit, _band(val, unit)

    # 전기밥솥 보강: 제목에 인용 없으면 모델코드에서 인용 추출(검증상 오류 0%).
    # 예) CRP-AHF[10]10 → 10인용, CR-[35]55 → 35인용. 코드 단위 첫 2자리 = 인용.
    if category_name == "전기밥솥":
        cm = _CODE_PERSON_RE.search((title or "").upper())
        if cm:
            v = int(cm.group(1))
            if 1 <= v <= 50:  # 밥솥 합리적 인용 범위(이상치 배제)
                return float(v), "인용", _band(float(v), "인용")
    return None, None, None


# 모델코드 첫 2자리 숫자(밥솥 인용): 'CRP-AHF10..' → 10, 'CR-35..' → 35
_CODE_PERSON_RE = re.compile(r"\b[A-Z]{2,5}-[A-Z]{0,3}(\d{2})")
