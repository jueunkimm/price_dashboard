"""초기 시드 데이터 — 카테고리 트리(기획서 4.1) + 쿠쿠 브랜드 별칭.

실행:  python -m app.seed
멱등(idempotent): 이미 있으면 건너뜀.
"""
from sqlalchemy import select

from app.database import Base, SessionLocal, engine
from app.models import Brand, Category

# 대분류: [(소분류명, 쿠쿠 라인업 여부, 검색 키워드)]
CATEGORY_TREE: dict[str, list[tuple[str, bool, str]]] = {
    "주방가전": [
        ("냉장고", False, "냉장고"),
        ("김치냉장고", False, "김치냉장고"),
        ("전기밥솥", True, "전기밥솥"),
        ("인덕션·전기레인지", True, "인덕션 전기레인지"),
        ("전자레인지·오븐", False, "전자레인지"),
        ("식기세척기", True, "식기세척기"),
        ("정수기", True, "정수기"),
        ("에어프라이어", False, "에어프라이어"),
        ("커피머신", False, "커피머신"),
        ("믹서·블렌더", False, "블렌더"),
        ("멀티쿠커", True, "멀티쿠커"),
        # 확장(쿠쿠 라인업 / 시장 모니터링)
        ("음식물처리기", True, "음식물처리기"),
        ("전기포트", True, "전기포트"),
        ("토스터", True, "토스터"),
        ("제빵기", True, "제빵기"),
        ("가스레인지", False, "가스레인지"),
        ("와인셀러", False, "와인셀러"),
        ("식물재배기", False, "식물재배기"),
        # 시장 모니터링 확장(다나와·에누리 기준)
        ("착즙기·원액기", False, "원액기"),
        ("전기그릴", False, "전기그릴"),
        ("전기프라이팬", False, "전기프라이팬"),
        ("튀김기", False, "튀김기"),
        ("광파오븐", False, "광파오븐"),
        ("가스오븐레인지", False, "가스오븐레인지"),
        ("제빙기", False, "제빙기"),
        ("식품건조기", False, "식품건조기"),
        ("요거트제조기", False, "요거트제조기"),
        ("탄산수제조기", False, "탄산수제조기"),
    ],
    "생활가전": [
        ("세탁기", False, "세탁기"),
        ("건조기", False, "건조기"),
        ("의류관리기", False, "의류관리기"),
        ("무선청소기", False, "무선청소기"),
        ("로봇청소기", False, "로봇청소기"),
        ("스팀다리미", False, "스팀다리미"),
        ("비데", True, "비데"),
        # 시장 모니터링 확장(청소기 세분·살균)
        ("유선청소기", False, "유선청소기"),
        ("침구청소기", False, "침구청소기"),
        ("스팀청소기", False, "스팀청소기"),
        ("살균기", False, "살균기"),
    ],
    "계절·환경가전": [
        ("에어컨", False, "에어컨"),
        ("선풍기·서큘레이터", False, "서큘레이터"),
        ("제습기", True, "제습기"),
        ("가습기", True, "가습기"),
        ("공기청정기", True, "공기청정기"),
        ("전기히터·온풍기", False, "전기히터"),
        # 확장(난방·계절)
        ("온수매트", True, "온수매트"),
        ("전기장판", False, "전기장판"),
        ("냉풍기", False, "냉풍기"),
    ],
    "영상·음향가전": [
        ("TV", False, "TV"),
        ("사운드바", False, "사운드바"),
        ("프로젝터", False, "프로젝터"),
        # 시장 모니터링 확장(음향)
        ("블루투스스피커", False, "블루투스스피커"),
        ("헤드폰·이어폰", False, "헤드폰"),
        ("홈시어터", False, "홈시어터"),
    ],
    "미용·건강가전": [
        ("헤어드라이어·스타일러", False, "헤어드라이어"),
        ("면도기", False, "전기면도기"),
        ("안마의자·안마기", True, "안마의자"),
        ("체중계", False, "체중계"),
        # 확장(미용·구강)
        ("전동칫솔", True, "전동칫솔"),
        ("구강세정기", False, "구강세정기"),
        ("피부미용기", False, "피부미용기"),
        # 시장 모니터링 확장(미용·건강측정)
        ("제모기", False, "제모기"),
        ("두피케어기", False, "두피케어기"),
        ("발마사지기", False, "발마사지기"),
        ("혈압계", False, "혈압계"),
        ("혈당계", False, "혈당계"),
        ("체온계", False, "체온계"),
    ],
}

# 자사(쿠쿠) 브랜드 별칭 사전
OWN_BRAND = {
    "name": "쿠쿠",
    "is_own": True,
    "aliases_json": ["쿠쿠", "CUCKOO", "Cuckoo", "쿠쿠전자", "쿠쿠홈시스"],
}


def seed() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # ── 브랜드 ──
        if not db.scalar(select(Brand).where(Brand.name == OWN_BRAND["name"])):
            db.add(Brand(**OWN_BRAND))
            db.commit()
            print(f"[seed] 브랜드 추가: {OWN_BRAND['name']} (별칭 {OWN_BRAND['aliases_json']})")
        else:
            print("[seed] 브랜드 이미 존재 — 건너뜀")

        # ── 카테고리 ──
        added = 0
        for major, subs in CATEGORY_TREE.items():
            parent = db.scalar(
                select(Category).where(Category.name == major, Category.level == 1)
            )
            if not parent:
                has_own = any(s[1] for s in subs)
                parent = Category(name=major, level=1, has_own_lineup=has_own)
                db.add(parent)
                db.flush()
                added += 1
            for sub_name, has_own, keyword in subs:
                exists = db.scalar(
                    select(Category).where(
                        Category.name == sub_name, Category.parent_id == parent.id
                    )
                )
                if not exists:
                    db.add(
                        Category(
                            name=sub_name,
                            parent_id=parent.id,
                            level=2,
                            has_own_lineup=has_own,
                            search_keyword=keyword,
                        )
                    )
                    added += 1
        db.commit()
        print(f"[seed] 카테고리 {added}개 추가 완료")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
