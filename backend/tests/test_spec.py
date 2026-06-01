"""카테고리별 규격 추출 회귀 테스트 — 정밀도(오인식 방지) 검증."""
from app.spec import band_for, extract_spec


class TestRiceCookerCodeCapacity:
    def test_code_person_when_title_missing(self):
        # 제목에 인용 없으면 밥솥 모델코드에서 인용 추출(검증상 오류 0%)
        v, u, b = extract_spec("전기밥솥", "쿠쿠전자 CUCKOO CRP-AHF1010FD 화이트")
        assert (v, u, b) == (10.0, "인용", "10인용")
        assert extract_spec("전기밥솥", "쿠쿠 CRP-DHP0610FD 다크실버")[2] == "6인용"
        assert extract_spec("전기밥솥", "CUCKOO CR-3555B 업소용")[2] == "35인용"

    def test_title_person_takes_precedence_over_code(self):
        # 제목 인용이 코드보다 우선
        assert extract_spec("전기밥솥", "쿠쿠 6인용 CRP-AHF1010FD")[0] == 6.0

    def test_code_capacity_only_for_rice_cooker(self):
        # 식기세척기는 코드 인용 미적용(삼성 DW80의 80은 인용 아님 → 오인식 방지)
        assert extract_spec("식기세척기", "삼성전자 비스포크 DW80F73Y1UEW 화이트")[1] is None


class TestCategoryAwareExtraction:
    def test_rice_cooker_uses_person_not_liter(self):
        # 밥솥의 '1.8L 내솥'을 L로 오인식하면 안 됨 → 인용만
        v, u, b = extract_spec("전기밥솥", "쿠쿠 10인용 1.8L 압력밥솥")
        assert (v, u, b) == (10.0, "인용", "10인용")

    def test_rice_cooker_liter_ignored(self):
        # 밥솥인데 인용 표기 없고 L만 있으면 → 추출 안 함(L은 밥솥 규격 아님)
        v, u, b = extract_spec("전기밥솥", "미니 압력밥솥 1.8L")
        assert u is None

    def test_washer_kg(self):
        v, u, b = extract_spec("세탁기", "삼성 그랑데 세탁기 24kg")
        assert (u, b) == ("kg", "24kg")

    def test_tv_inch(self):
        v, u, b = extract_spec("TV", "LG 올레드 65형 4K")
        assert (u, b) == ("형", "65형")

    def test_induction_burners(self):
        v, u, b = extract_spec("인덕션·전기레인지", "쿠쿠 3구 인덕션")
        assert (u, b) == ("구", "3구")

    def test_coffee_bar(self):
        v, u, b = extract_spec("커피머신", "드롱기 19Bar 전자동 커피머신")
        assert (u, b) == ("bar", "19Bar")

    def test_soundbar_channel(self):
        v, u, b = extract_spec("사운드바", "삼성 5.1채널 사운드바")
        assert u == "ch" and b == "5.1채널"

    def test_no_spec_category(self):
        # 비데/로봇청소기 등은 표준 수치 규격 없음 → None
        assert extract_spec("비데", "쿠쿠 인스퓨어 비데 자동") == (None, None, None)
        assert extract_spec("로봇청소기", "로보락 S10 물통형") == (None, None, None)

    def test_band_for_recompute(self):
        assert band_for(65.0, "형") == "65형"
        assert band_for(3.0, "구") == "3구"
        assert band_for(None, None) is None
