"""세부유형 보강(enrich) 테스트 — 제목분류·모델코드추출·재조회 다수결.

네트워크 없이 순수 로직만 검증.
"""
from collector.enrich_subcategory import (
    _model_code,
    _resolve_subtype,
    _title_subtype,
)


def test_title_subtype_strong_signal():
    assert _title_subtype("전기밥솥", "쿠쿠 CRP 압력밥솥 6인용") == "압력밥솥"
    assert _title_subtype("정수기", "코웨이 냉온정수기 CHP-...") == "냉온정수기"
    assert _title_subtype("세탁기", "LG 트롬 드럼 세탁기 9kg") == "드럼세탁기"
    assert _title_subtype("냉장고", "삼성 양문형 냉장고 846L") == "양문형냉장고"


def test_title_subtype_no_signal_returns_none():
    # 강한 신호 없으면 None(추측 금지) → 방법 C로 넘어감
    assert _title_subtype("전기밥솥", "쿠쿠전자 CUCKOO CR-1075S 실버") is None
    assert _title_subtype("세탁기", "쿠쿠전자 CUCKOO CWM-ATFF1210B 블루블랙") is None


def test_model_code_extraction():
    assert _model_code("쿠쿠전자 CUCKOO CWM-ATFF1210B 블루블랙") == "CWM-ATFF1210B"
    assert _model_code("쿠잉 무전원정수기 WP-N01WH 직수형") == "WP-N01WH"
    assert _model_code("그냥 한글 제품명만 있음") is None


def test_resolve_subtype_majority_and_code_guard():
    code = "CWM-ATFF1210B"
    items = [
        {"sub_category": "일반세탁기", "title": "쿠쿠 CWM-ATFF1210B 블루블랙"},
        {"sub_category": "일반세탁기", "title": "쿠쿠 CWM-ATFF1210B 화이트"},
        # 코드가 제목에 없는 항목은 무시(충돌 방지)
        {"sub_category": "드럼세탁기", "title": "엉뚱한 다른 모델 ABC-9999"},
    ]
    assert _resolve_subtype(items, code) == "일반세탁기"


def test_resolve_subtype_none_when_no_match():
    # 코드가 어떤 제목에도 없거나 category4가 비면 None
    items = [
        {"sub_category": "", "title": "쿠쿠 CWM-ATFF1210B 블루블랙"},
        {"sub_category": "일반세탁기", "title": "전혀 다른 제품 XYZ-1111"},
    ]
    assert _resolve_subtype(items, "CWM-ATFF1210B") is None
