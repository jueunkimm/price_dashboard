"""상품 텍스트 분석 유틸 — 렌탈/부품 판별, 모델키·용량 추출.

비교 가능한 '제품' 풀을 만들기 위한 정제 로직(QA A-3/A-4/B-1 대응).
- 렌탈: 월렌탈료가 표시가로 잡혀 일시불가와 섞임 → 집계 분리
- 부품/소모품: 필터·내솥 등 본품이 아닌 항목 → 비교 제외
- 모델키: 같은 모델의 몰별 중복 리스팅을 묶어 모델 단위 집계
- 용량: 동급(같은 용량대) 비교를 위한 스펙 정규화
"""
from __future__ import annotations

import re

# 렌탈/약정 신호 키워드
_RENTAL_KEYWORDS = (
    "렌탈",
    "렌털",
    "약정",
    "의무사용",
    "의무 사용",
    "자가관리",
    "방문관리",
    "개월약정",
    "개월 약정",
    "월렌탈",
    "월 렌탈",
    "렌탈료",
    # 구독형(월 구독료가 표시가로 잡힘) — 일시불과 분리
    "구독",
    "월구독",
    "월 구독",
    "월정액",
    "월요금",
)

# 의무사용기간(약정) 신호: '의무36개월', '의무72' 등 — 구독/렌탈 약정
_COMMITMENT_RE = re.compile(r"의무\s?\d+")


def is_rental_title(title: str) -> bool:
    """제목에 렌탈/약정/구독 신호가 있으면 True.

    주의: '구독권'(꽃 구독권 등 사은품 번들)·'멤버십적립'(적립 할인)은
    구독형 제품이 아니므로 오탐 방지를 위해 제외한다.
    """
    t = title or ""
    probe = t.replace("구독권", "")  # 번들 사은품 '구독권' 제거 후 검사
    if any(k in probe for k in _RENTAL_KEYWORDS):
        return True
    if _COMMITMENT_RE.search(t):
        return True
    return False


# 부품/소모품/악세서리 신호 — 본품이 아닌 항목(비교 풀에서 제외)
# 주의: 단독 '필터'는 본품명에도 등장(예: 필터정수기)하므로 제외. 조합/명시 키워드만.
_ACCESSORY_KEYWORDS = (
    "호환",
    "정품필터",
    "리필필터",
    "교체필터",
    "필터세트",
    "내솥",
    "이너팟",
    "내통",
    "패킹",
    "고무패킹",
    "소모품",
    "케이스",
    "전용커버",
    "거치대",
    "받침대",
    "브러시",
    "노즐",
    "악세서리",
    "액세서리",
    "부속품",
    "부속",
    "전용가방",
    "파우치",
    # 부품/소모품 보강 — 가격 왜곡 유발 항목(이상치 감사 기반, 고신뢰 키워드만)
    "반죽날개",
    "오븐망",
    "발열팬",
    "도포기",
    "면도기날",
    "면도날",
    "거름망",
    "채반",
    "정품부품",
    "전용필터",
    "교체날",
)


def is_accessory_title(title: str) -> bool:
    """제목에 부품/소모품 신호가 있으면 True."""
    t = title or ""
    return any(k in t for k in _ACCESSORY_KEYWORDS)


# 리셀러(드롭십) 스팸 — '쿠쿠' 브랜드 검색에 딸려오지만 카테고리와 무관한 잡화를
# 스팸성 다중키워드 제목으로 파는 재판매몰. 자사도 본품도 아니어서 비교를 흐린다.
# (예: '쿠쿠스토어 사이클링 양말…', '쿠쿠스토어 면도기 걸이 랙…')
# 진짜 쿠쿠 제품은 '쿠쿠전자/쿠쿠홈시스'이지 '쿠쿠스토어'가 아니므로 오제외 위험 없음.
_RESELLER_MARKERS = ("쿠쿠스토어",)


def is_reseller_spam(title: str) -> bool:
    """알려진 리셀러(드롭십) 잡화 제목이면 True — 비교 풀에서 제외."""
    n = (title or "").replace(" ", "")
    return any(m in n for m in _RESELLER_MARKERS)


# 모델코드: 알파벳 prefix + 하이픈 + 영숫자 (CRP-LHTR1010FGWM)
_MODEL_CODE_RE = re.compile(r"\b([A-Z]{2,5}-[A-Z0-9]{3,})")


def extract_model_key(title: str) -> str | None:
    """제목에서 모델 단위 dedup 키(모델코드) 추출. 없으면 None.

    색상/옵션이 달라도 같은 모델코드면 동일 모델로 묶기 위함.
    """
    if not title:
        return None
    m = _MODEL_CODE_RE.search(title.upper())
    return m.group(1) if m else None


# 용량 패턴: '10인용', '6인', '12kg', '12L', '8.5L', '20평', '65형', '55인치'
_CAP_PERSON_RE = re.compile(r"(\d+)\s*인(?!치)용?")  # '인치'(TV)는 제외
_CAP_KG_RE = re.compile(r"(\d+(?:\.\d+)?)\s*kg", re.IGNORECASE)
_CAP_INCH_RE = re.compile(r"(\d{2,3})\s*(?:형|인치)")
_CAP_LITER_RE = re.compile(r"(\d+(?:\.\d+)?)\s*[lL리터]")
_CAP_PYEONG_RE = re.compile(r"(\d+)\s*평")


def extract_capacity(title: str) -> tuple[float | None, str | None]:
    """제목에서 (용량값, 단위) 추출. 인용 > kg > 형/인치 > 평 > L 순 우선.

    인용(밥솥) / kg(세탁·건조) / 형·인치(TV) / 평(공기청정·에어컨) / L(전자레인지·냉장고).
    """
    t = title or ""
    m = _CAP_PERSON_RE.search(t)
    if m:
        return float(m.group(1)), "인용"
    m = _CAP_KG_RE.search(t)
    if m:
        return float(m.group(1)), "kg"
    m = _CAP_INCH_RE.search(t)
    if m:
        return float(m.group(1)), "형"
    m = _CAP_PYEONG_RE.search(t)
    if m:
        return float(m.group(1)), "평"
    m = _CAP_LITER_RE.search(t)
    if m:
        return float(m.group(1)), "L"
    return None, None


def capacity_band(value: float | None, unit: str | None) -> str | None:
    """용량을 동급 비교용 구간 라벨로. 예: 6인용→'6인용', 12L→'10~15L'."""
    if value is None or unit is None:
        return None
    if unit == "인용":
        return f"{int(value)}인용"
    if unit == "kg":
        return f"{int(value)}kg"  # 세탁·건조는 표준 용량(9/12/24kg 등)
    if unit == "형":
        return f"{int(value)}형"  # TV 인치(55/65/75형 등)
    if unit == "평":
        lo = (int(value) // 10) * 10
        return f"{lo}~{lo + 10}평"
    if unit == "L":
        lo = int(value // 5) * 5
        return f"{lo}~{lo + 5}L"
    return None
