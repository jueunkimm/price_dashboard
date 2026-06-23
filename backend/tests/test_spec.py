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
        assert (u, b) == ("kg", "20~24kg")  # 다나와식 구간

    def test_tv_inch(self):
        v, u, b = extract_spec("TV", "LG 올레드 65형 4K")
        assert (u, b) == ("형", "56~65형")  # 다나와식 구간

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
        assert band_for(65.0, "형") == "56~65형"
        assert band_for(3.0, "구") == "3구"
        assert band_for(870.0, "L") == "800~900L"
        assert band_for(12.0, "kg") == "10~14kg"
        assert band_for(None, None) is None


class TestExpandedUnits:
    def test_wine_cellar_bottles(self):
        v, u, b = extract_spec("와인셀러", "캐리어 와인셀러 32병 스탠드형")
        assert u == "병" and b == "19~50병"
        assert extract_spec("와인셀러", "소형 와인냉장고 12병")[2] == "~18병"

    def test_frypan_cm(self):
        v, u, b = extract_spec("전기프라이팬", "키친아트 전기그릴팬 28cm 양면")
        assert (v, u, b) == (28.0, "cm", "28cm")

    def test_food_dryer_trays(self):
        v, u, b = extract_spec("식품건조기", "리큅 식품건조기 5단 트레이")
        assert (u, b) == ("단", "5단")

    def test_kettle_liter(self):
        assert extract_spec("전기포트", "테팔 전기포트 1.7L")[2] == "~3L"

    def test_fridge_liter_100band(self):
        # 냉장고는 100L 구간(소형가전 L과 규모 구분)
        assert extract_spec("냉장고", "삼성 비스포크 4도어 냉장고 870L")[2] == "800~900L"
        assert extract_spec("전자레인지·오븐", "광파오븐 23L")[2] == "20~30L"

    def test_gas_range_burners(self):
        assert extract_spec("가스레인지", "린나이 가스레인지 3구")[2] == "3구"

    def test_ice_maker_kg(self):
        assert extract_spec("제빙기", "카이저 제빙기 일 51kg")[1] == "kg"

    def test_heatmat_size_text(self):
        v, u, b = extract_spec("온수매트", "일월 온수매트 퀸 150x200")
        assert u == "size" and b == "퀸"
        assert extract_spec("온수매트", "슈퍼싱글 온수매트")[2] == "슈퍼싱글"
        assert band_for(4.0, "size") == "퀸"

    def test_electric_mat_person_first(self):
        # 전기장판은 인용 우선
        assert extract_spec("전기장판", "1인용 전기장판 싱글")[2] == "1인용"

    def test_projector_lumen(self):
        v, u, b = extract_spec("프로젝터", "엡손 빔프로젝터 3300안시루멘 풀HD")
        assert u == "루멘" and b == "3000~6000lm"
        assert extract_spec("프로젝터", "미니 LED 프로젝터 9000루멘")[2] == "6000lm~"

    def test_clothescare_garments(self):
        assert extract_spec("의류관리기", "LG 스타일러 5벌 블랙")[2] == "5벌"

    def test_vacuum_pa_from_danawa_spec(self):
        # 다나와 spec_list의 흡입력(Pa, 콤마 포함) — 네이버 제목엔 없는 사양
        assert extract_spec("로봇청소기", "로봇청소기 / 흡입력 : 5,000Pa / 사용시간")[2] == "5000~8000Pa"
        assert extract_spec("무선청소기", "핸디스틱청소기 / 무선 / 흡입력 : 21,000Pa")[2] == "12000Pa~"
