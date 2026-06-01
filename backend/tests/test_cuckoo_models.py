"""쿠쿠 모델코드 사전 회귀 테스트 — 경쟁사 오탐(쿠첸/코웨이/코지마) 방지 검증."""
from app.cuckoo_models import cuckoo_code_in


class TestModelCodeCategoryGating:
    def test_cuckoo_code_in_right_category(self):
        assert cuckoo_code_in("쿠쿠 CRP-DHP0610FW 화이트", "전기밥솥") == "CRP"
        assert cuckoo_code_in("AC-28AHNL20F 공기청정기", "공기청정기") == "AC"

    def test_code_in_wrong_category_rejected(self):
        # AC 코드인데 카테고리가 정수기면 매칭 안 됨(게이팅)
        assert cuckoo_code_in("AC-28AHNL20F", "정수기") is None

    def test_no_code(self):
        assert cuckoo_code_in("쿠쿠 스피드팟 멀티쿠커", "멀티쿠커") is None


class TestCompetitorPrefixCollision:
    """경쟁사도 C__- 형식을 쓰므로 사전엔 있으나, 매처에서 brand_raw로 걸러야 함.
    여기서는 prefix 자체는 카테고리에 부합하면 잡히는 것이 정상(매처가 추가 게이팅)."""

    def test_cir_is_induction_prefix(self):
        # 쿠첸 CIR-EB330 도 CIR → 인덕션 prefix 자체는 매칭됨.
        # (실제 자사 판정은 BrandMatcher가 brand_raw=쿠첸 으로 차단)
        assert cuckoo_code_in("쿠첸 CIR-EB330TOB2", "인덕션·전기레인지") == "CIR"
