"""정제 로직 회귀 테스트 — QA에서 드러난 위험 지점 보호."""
from app.textutil import (
    capacity_band,
    extract_capacity,
    extract_model_key,
    is_accessory_title,
    is_rental_title,
)


class TestRental:
    def test_rental_detected(self):
        assert is_rental_title("쿠쿠 안마의자 렌탈 레스티노 72개월약정 CMS-J310BR")
        assert is_rental_title("코웨이 CP-6201N 자가관리, 의무사용 72개월")

    def test_outright_not_rental(self):
        assert not is_rental_title("쿠쿠전자 CUCKOO CRP-EHB0310FW 화이트 실버")


class TestAccessory:
    def test_accessory_detected(self):
        assert is_accessory_title("쿠쿠 밥솥 호환 고무패킹 내솥")
        assert is_accessory_title("정수기 정품필터 리필필터 세트")

    def test_main_product_not_accessory(self):
        # '필터' 단독은 본품명에도 등장 → 부품으로 보면 안 됨
        assert not is_accessory_title("쿠쿠 인스퓨어 필터 비데 CBT-G1032MW")
        assert not is_accessory_title("쿠쿠전자 CUCKOO CRP-DHP0610FD 다크실버")


class TestModelKey:
    def test_extracts_code(self):
        assert extract_model_key("쿠쿠전자 CUCKOO CRP-LHTR1010FGWM 그레이스 화이트") == "CRP-LHTR1010FGWM"
        assert extract_model_key("삼성 RS70F65Q2Y 코타 화이트") is None  # 하이픈 없으면 None
        assert extract_model_key("LG Z323MEF") is None  # 하이픈 없음

    def test_same_model_diff_color_same_key(self):
        a = extract_model_key("CUCKOO CRP-DHP0610FW 화이트")
        b = extract_model_key("쿠쿠 CRP-DHP0610FW 블랙 단품")
        assert a == b == "CRP-DHP0610FW"


class TestCapacity:
    def test_person(self):
        assert extract_capacity("쿠쿠 10인용 압력밥솥") == (10.0, "인용")

    def test_liter(self):
        assert extract_capacity("쿠쿠 전자레인지 23L 화이트") == (23.0, "L")

    def test_pyeong(self):
        assert extract_capacity("쿠쿠 공기청정기 28평형") == (28.0, "평")

    def test_kg(self):
        assert extract_capacity("삼성 그랑데 세탁기 24kg WF24") == (24.0, "kg")

    def test_inch(self):
        assert extract_capacity("LG 올레드 65형 4K TV") == (65.0, "형")
        assert extract_capacity("삼성 55인치 QLED") == (55.0, "형")

    def test_priority_person_over_liter(self):
        # 인용이 L보다 우선
        assert extract_capacity("쿠쿠 10인용 1.8L 압력밥솥") == (10.0, "인용")

    def test_none(self):
        assert extract_capacity("쿠쿠 CRP-EHB0310FW 화이트") == (None, None)

    def test_band(self):
        assert capacity_band(10.0, "인용") == "10인용"
        assert capacity_band(24.0, "kg") == "24kg"
        assert capacity_band(65.0, "형") == "65형"
        assert capacity_band(23.0, "L") == "20~25L"
        assert capacity_band(28.0, "평") == "20~30평"
        assert capacity_band(None, None) is None
