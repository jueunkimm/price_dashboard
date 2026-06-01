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
    ],
    "생활가전": [
        ("세탁기", False, "세탁기"),
        ("건조기", False, "건조기"),
        ("의류관리기", False, "의류관리기"),
        ("무선청소기", False, "무선청소기"),
        ("로봇청소기", False, "로봇청소기"),
        ("스팀다리미", False, "스팀다리미"),
        ("비데", True, "비데"),
    ],
    "계절·환경가전": [
        ("에어컨", False, "에어컨"),
        ("선풍기·서큘레이터", False, "서큘레이터"),
        ("제습기", True, "제습기"),
        ("가습기", True, "가습기"),
        ("공기청정기", True, "공기청정기"),
        ("전기히터·온풍기", False, "전기히터"),
    ],
    "영상·음향가전": [
        ("TV", False, "TV"),
        ("사운드바", False, "사운드바"),
        ("프로젝터", False, "프로젝터"),
    ],
    "미용·건강가전": [
        ("헤어드라이어·스타일러", False, "헤어드라이어"),
        ("면도기", False, "전기면도기"),
        ("안마의자·안마기", True, "안마의자"),
        ("체중계", False, "체중계"),
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
