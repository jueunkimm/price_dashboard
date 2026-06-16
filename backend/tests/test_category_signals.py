"""category_signals.route_target 회귀 테스트 — 오교정 0(고정밀) 보장.

실데이터 시뮬레이션에서 정타로 확인된 이동과, 반드시 '이동 안 함'이어야 하는
까다로운 케이스(기능중첩·부속품·정배치·인접쌍)를 함께 고정한다.
"""
from app.category_signals import route_target

TRACKED = {
    "전기밥솥", "면도기", "냉장고", "김치냉장고", "음식물처리기", "식품건조기",
    "정수기", "커피머신", "멀티쿠커", "에어프라이어", "제빵기", "전기장판", "온수매트",
    "제모기", "탄산수제조기", "의류관리기", "제습기", "식기세척기", "인덕션·전기레인지",
    "와인셀러", "프로젝터", "홈시어터", "가스오븐레인지", "안마의자·안마기", "발마사지기",
    "블루투스스피커",
}


def r(title, current):
    return route_target(title, current, TRACKED)


class TestRoutesRealBugs:
    def test_ricecooker_in_shaver(self):
        # 핵심 버그: '쿠쿠 면도기' 보조검색에 섞인 압력밥솥
        assert r("쿠쿠 IH 압력밥솥 2기압 /2인용/3인용/미니/쾌속취사", "면도기") == "전기밥솥"

    def test_ricecooker_in_fridge(self):
        assert r("쿠쿠 소형 3인용 미니 전기압력밥솥 그레이스 화이트 1등급", "냉장고") == "전기밥솥"

    def test_foodwaste_in_dryer(self):
        assert r("쿠쿠 음식물처리기 CFD-D301DCNW 배송무료", "식품건조기") == "음식물처리기"

    def test_dishwasher_in_induction(self):
        assert r("삼성 비스포크 14인용 AI 히든 식기세척기 화이트 슬림핏 인덕션", "인덕션·전기레인지") == "식기세척기"

    def test_projector_misfiled(self):
        # 빔프로젝터가 다른 카테고리에 섞이면 프로젝터로(현 카테고리 신호 없을 때만)
        assert r("미니 빔프로젝터 휴대용 4K LED 가정용", "블루투스스피커") == "프로젝터"


class TestNeverMisroutes:
    def test_correctly_placed_untouched(self):
        # 정배치 — 제목에 현 카테고리 신호가 있으면 건드리지 않음
        assert r("쿠쿠 트윈프레셔 압력밥솥 CRP-LHTR0610FB", "전기밥솥") is None

    def test_kimchi_fridge_substring_not_dragged(self):
        # '김치 냉장고'(공백)·'김치톡톡냉장고'가 '냉장고'로 끌려가지 않음(냉장고 제외)
        assert r("캐리어 클라윈드 미니 소형 김치 냉장고 93L 스탠드형", "김치냉장고") is None
        assert r("[구독] 쿠쿠 미식 컬렉션 김치 냉장고 CKR-BFFD1230GEG", "김치냉장고") is None

    def test_feature_word_not_misrouted(self):
        # 부속품/기능어로 인한 오교정 차단
        assert r("쿠쿠 인스퓨어 정수필터 CPPU-C1710CP 커피머신 온수기 헤드 포함", "정수기") is None
        assert r("필립스 탄산수 제조기 소다 메이커 정수기 주입기 실린더", "탄산수제조기") is None

    def test_ambiguous_pairs_not_routed(self):
        # 기능중첩 인접쌍 — 자동 라우팅 금지
        assert r("쿠쿠 전기압력 밥솥 겸용 멀티쿠커", "멀티쿠커") is None
        assert r("쿠쿠 오븐에어프라이어 5가지기능 토스터기 제빵기 식품건조기", "에어프라이어") is None
        assert r("nimin 여성 브라질리언 제모기 비키니라인 면도기 Y존", "제모기") is None

    def test_no_signal_untouched(self):
        assert r("브라운 전기면도기 9시리즈 9PRO", "면도기") is None
