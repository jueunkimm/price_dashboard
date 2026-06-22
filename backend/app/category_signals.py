"""제목 기반 카테고리 정합성 — '배타적 제품유형' 신호로 명백한 오배치를 잡는다.

배경: 카테고리 검색/자사 보조검색('쿠쿠 {카테고리}')이 검색어와 무관한 제품을
끌어와 엉뚱한 카테고리에 섞인다(예: '쿠쿠 면도기' 검색 결과에 쿠쿠 압력밥솥).
모델코드가 없으면 카탈로그/prefix 라우팅이 못 잡고, naver_cat이 비면 off_category도
못 잡는다. 이를 보완해 '제목의 배타적 제품유형'으로 교정/차단한다.

설계 원칙(오교정 0 목표 — 고정밀):
  - DECISIVE: '이 단어가 있으면 그 제품이 거의 확실'한 배타적 유형만(기능중첩 제외).
  - 기능이 겹치는 유형(에어프라이어/멀티쿠커/광파오븐/냉풍기·선풍기/홈시어터·사운드바
    /온수매트·전기장판/제모기·면도기 등)은 AMBIG로 자동 라우팅 금지.
  - 냉장고/김치냉장고는 substring 충돌(‘김치냉장고’⊃‘냉장고’)로 제외.
  - 현 카테고리 자체 신호가 제목에 있으면(정배치/겸용) 건드리지 않음.
  - 부속품 추정어(필터·헤드 등)는 별매품 영역이라 라우팅하지 않음.
실데이터 6,900건 시뮬레이션에서 제안 이동 7건 전부 정타(오교정 0) 확인.
"""
from __future__ import annotations

# 배타적 제품유형 키워드 → 표준 카테고리명
DECISIVE: dict[str, str] = {
    "압력밥솥": "전기밥솥", "전기밥솥": "전기밥솥", "보온밥솥": "전기밥솥", "밥솥": "전기밥솥",
    "정수기": "정수기", "비데": "비데", "제습기": "제습기", "가습기": "가습기",
    "식기세척기": "식기세척기", "식세기": "식기세척기",
    "음식물처리기": "음식물처리기",
    "로봇청소기": "로봇청소기", "제빙기": "제빙기", "공기청정기": "공기청정기",
    "전동칫솔": "전동칫솔", "구강세정기": "구강세정기", "워터픽": "구강세정기",
    "체온계": "체온계", "체중계": "체중계", "체지방계": "체중계",
    "혈압계": "혈압계", "혈당계": "혈당계",
    "프로젝터": "프로젝터", "빔프로젝터": "프로젝터",
    "와인셀러": "와인셀러", "와인냉장고": "와인셀러",
    "식물재배기": "식물재배기", "새싹재배기": "식물재배기",
    "커피머신": "커피머신", "에스프레소머신": "커피머신",
    "제빵기": "제빵기", "탄산수제조기": "탄산수제조기",
    "전기면도기": "면도기", "전동면도기": "면도기",
    "안마의자": "안마의자·안마기",
    # 세탁/건조 — '미니 의류건조기'가 세탁기에 섞이는 것만 분리. '세탁건조기 일체형'은
    # 세탁기로 귀속(다나와도 세탁기건조기일체형은 세탁기 하위). 식품건조기는 별도 등록해
    # '건조기' substring 오라우팅 방지. (더 구체적 키워드가 우선 — nested substring 해소)
    "세탁기": "세탁기", "세탁건조기": "세탁기", "세탁기건조기": "세탁기",
    "의류건조기": "건조기", "건조기": "건조기",
    "식품건조기": "식품건조기",
}

# 기능 중첩/인접으로 자동 라우팅을 금지하는 카테고리 쌍(방향 무관)
AMBIG: set[frozenset] = {
    frozenset(x) for x in [
        ("에어프라이어", "제빵기"), ("멀티쿠커", "전기밥솥"), ("멀티쿠커", "제빵기"),
        ("온수매트", "전기장판"), ("제모기", "면도기"), ("침구청소기", "로봇청소기"),
        ("침구청소기", "스팀청소기"), ("의류관리기", "제습기"), ("정수기", "커피머신"),
        ("탄산수제조기", "정수기"), ("와인셀러", "냉장고"), ("토스터", "제빵기"),
        ("전기그릴", "제빵기"), ("에어프라이어", "멀티쿠커"),
    ]
}

# 부속품 추정어 — 있으면 라우팅하지 않음(별매품 처리 영역)
ACC_HINT = ("필터", "헤드", "거치대", "받침", "커버", "전용 ", "호환", "교체", "스탠드만")

_KWS = sorted(DECISIVE, key=len, reverse=True)
_OWN_KW: dict[str, set[str]] = {}
for _k, _v in DECISIVE.items():
    _OWN_KW.setdefault(_v, set()).add(_k)


def _norm(t: str) -> str:
    return (t or "").replace(" ", "")


def signal_categories(title: str) -> set[str]:
    """제목에서 감지된 배타적 제품유형 카테고리 집합(중첩 substring 해소)."""
    n = _norm(title)
    matched = [k for k in _KWS if k in n]
    out = [k for k in matched if not any(k != o and k in o for o in matched)]
    return {DECISIVE[k] for k in out}


def route_target(title: str, current: str, tracked: set[str]) -> str | None:
    """제목의 배타적 유형이 current와 명백히 다르면 옮겨야 할 카테고리명, 아니면 None.

    collect(차단)·recategorize(교정) 공용. current/대상이 tracked에 있을 때만 동작.
    """
    n = _norm(title)
    sig = {c for c in signal_categories(title) if c in tracked}
    if not sig or current in sig:
        return None
    # 현 카테고리 자체 신호(키워드/이름)가 제목에 있으면 정배치/겸용 → 건드리지 않음
    own = _OWN_KW.get(current, set()) | {current}
    if any(k and _norm(k) in n for k in own):
        return None
    if any(h in title for h in ACC_HINT):
        return None
    dest = sig - {current}
    if len(dest) != 1:
        return None
    target = next(iter(dest))
    if target not in tracked or frozenset((current, target)) in AMBIG:
        return None
    return target
