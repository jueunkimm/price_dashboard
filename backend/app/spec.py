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
    "W": re.compile(r"(\d{1,2},\d{3}|\d{3,4})\s*w(?:att)?", re.IGNORECASE),
    "병": re.compile(r"(\d+)\s*병"),  # 와인셀러 수납 병수
    "cm": re.compile(r"(\d{2,3})\s*cm", re.IGNORECASE),  # 전기프라이팬 조리면 지름 등
    "단": re.compile(r"(\d+)\s*단"),  # 식품건조기 트레이 단수
    "루멘": re.compile(r"(\d{3,5})\s*(?:안시|ansi|루멘|lm)", re.IGNORECASE),  # 프로젝터 밝기
    "벌": re.compile(r"(\d+)\s*벌"),  # 의류관리기 수용량
    "Pa": re.compile(r"(\d[\d,]{2,})\s*pa", re.IGNORECASE),  # 청소기 흡입력(다나와 사양)
}

# 침대 규격(온수매트·전기장판) — 텍스트 규격을 순위 숫자로 저장하고 라벨로 환원.
_SIZE_RANK = {"슈퍼싱글": 2, "라지킹": 6, "초킹": 6, "싱글": 1, "더블": 3, "퀸": 4, "킹": 5}
_SIZE_WORD = {1: "싱글", 2: "슈퍼싱글", 3: "더블", 4: "퀸", 5: "킹", 6: "킹+"}
_SIZE_RE = re.compile(r"(슈퍼싱글|라지킹|초킹|싱글|더블|퀸|킹)")


def band_for(value: float | None, unit: str | None) -> str | None:
    """저장된 (값, 단위)로부터 밴드 라벨 재계산. 집계에서 사용."""
    if value is None or unit is None:
        return None
    if unit == "size":
        return _SIZE_WORD.get(int(value))
    if unit not in _PATTERNS:
        return None
    return _band(value, unit)


def _band(value: float, unit: str) -> str:
    """동급 비교용 구간 라벨. 큰 규모 단위(kg·L·평·형)는 다나와식 '범위 구간'으로
    묶어 파편화를 막고, L은 규모 인식(소형가전 vs 냉장고)으로 구간 폭을 달리한다."""
    if unit == "인용":
        return f"{int(value)}인용"
    if unit == "kg":
        # 다나와식 세탁/건조 용량 구간
        if value < 4:
            return "~3kg"
        if value < 10:
            return "4~9kg"
        if value < 15:
            return "10~14kg"
        if value < 20:
            return "15~19kg"
        if value < 25:
            return "20~24kg"
        return "25kg~"
    if unit == "형":
        if value < 33:
            return "~32형"
        if value < 44:
            return "33~43형"
        if value < 56:
            return "44~55형"
        if value < 66:
            return "56~65형"
        if value < 76:
            return "66~75형"
        return "76형~"
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
        if value < 7:
            return "~6평"
        if value < 11:
            return "7~10평"
        if value < 16:
            return "11~15평"
        if value < 19:
            return "16~18평"
        if value < 30:
            return "19~29평"
        lo = int(value // 10) * 10
        return f"{lo}~{lo + 10}평"
    if unit == "L":
        # 규모 인식: 소형가전(포트·에어프라이어)은 좁게, 냉장고는 100L 구간(다나와식)
        if value < 4:
            return "~3L"
        if value < 7:
            return "4~6L"
        if value < 11:
            return "7~10L"
        if value < 15:
            return "11~14L"
        if value < 20:
            return "15~19L"
        if value < 100:
            lo = int(value // 10) * 10
            return f"{lo}~{lo + 10}L"
        lo = int(value // 100) * 100
        return f"{lo}~{lo + 100}L"
    if unit == "병":
        v = int(value)
        if v <= 18:
            return "~18병"
        if v <= 50:
            return "19~50병"
        if v <= 100:
            return "51~100병"
        return "100병+"
    if unit == "cm":
        return f"{int(value)}cm"
    if unit == "단":
        return f"{int(value)}단"
    if unit == "벌":
        return f"{int(value)}벌"
    if unit == "Pa":  # 청소기 흡입력(다나와)
        v = int(value)
        if v < 2000:
            return "~2000Pa"
        if v < 5000:
            return "2000~5000Pa"
        if v < 8000:
            return "5000~8000Pa"
        if v < 12000:
            return "8000~12000Pa"
        return "12000Pa~"
    if unit == "루멘":  # 프로젝터 밝기(안시/LED루멘 혼재 → 폭넓은 구간)
        v = int(value)
        if v < 1000:
            return "~1000lm"
        if v < 3000:
            return "1000~3000lm"
        if v < 6000:
            return "3000~6000lm"
        return "6000lm~"
    if unit == "size":
        return _SIZE_WORD.get(int(value), str(value))
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
    "광파오븐": ["L"],
    "에어프라이어": ["L"],
    "튀김기": ["L"],
    "믹서·블렌더": ["L"],
    "전기포트": ["L"],
    "음식물처리기": ["L"],
    "정수기": [],  # 직수/저수조 — 표준 수치 규격 아님
    "커피머신": ["bar"],
    "인덕션·전기레인지": ["구"],
    "가스레인지": ["구"],
    "가스오븐레인지": ["구"],
    "전기프라이팬": ["cm"],
    "제빙기": ["kg"],  # 일일 제빙량
    "식품건조기": ["단"],  # 트레이 단수
    "와인셀러": ["병"],
    "세탁기": ["kg"],
    "건조기": ["kg"],
    "의류관리기": ["벌", "kg"],  # 다나와 수용량(벌)
    "프로젝터": ["루멘"],  # 다나와 밝기 필터
    "무선청소기": ["Pa"],  # 다나와 흡입력(Pa). 소비전력 W는 흡입력과 혼동되어 제외
    "유선청소기": ["W"],  # 흡입력/소비전력(W). L은 흡입력·풍량 오인식 노이즈라 제외
    "로봇청소기": ["Pa"],  # 다나와 흡입력(제목엔 없고 다나와 사양에 있음)
    "토스터": ["구"],  # 투입구 수
    "스팀다리미": ["W"],
    "비데": [],
    "에어컨": ["평"],
    "선풍기·서큘레이터": [],
    "제습기": ["L"],
    "가습기": ["L"],
    "공기청정기": ["평"],
    "전기히터·온풍기": ["W"],
    "온수매트": ["size"],  # 침대 규격(싱글/퀸/킹)
    "전기장판": ["인용", "size"],
    "TV": ["형"],
    "사운드바": ["ch"],
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
        if unit == "size":  # 텍스트 규격(침대 사이즈) — 순위 숫자로 저장
            sm = _SIZE_RE.search(title)
            if sm:
                rank = _SIZE_RANK[sm.group(1)]
                return float(rank), "size", _SIZE_WORD.get(rank, sm.group(1))
            continue
        m = _PATTERNS[unit].search(title)
        if m:
            val = float(m.group(1).replace(",", ""))  # '10,000Pa' 등 콤마 제거
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
