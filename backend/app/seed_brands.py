"""경쟁사 브랜드 시드(B-2) — 주요 가전 브랜드 별칭 등록.

매처가 brand.aliases_json 을 순회하므로, 등록 시 brand_raw='삼성전자' 등이
자동으로 brand_id에 매핑된다(is_own=False). 이를 통해 브랜드별 가격/변동 비교 가능.
실행:  python -m app.seed_brands
"""
from sqlalchemy import select

from app.database import Base, SessionLocal, engine
from app.models import Brand

# (표준명, [별칭...]) — 자사(쿠쿠) 제외 경쟁/주요 브랜드
COMPETITORS: list[tuple[str, list[str]]] = [
    ("삼성전자", ["삼성", "SAMSUNG", "삼성전자"]),
    ("LG전자", ["LG", "엘지", "LG전자", "LG ELECTRONICS"]),
    ("위니아", ["위니아", "WINIA", "딤채", "위니아딤채"]),
    ("쿠첸", ["쿠첸", "CUCHEN"]),
    ("코웨이", ["코웨이", "COWAY"]),
    ("SK매직", ["SK매직", "SK MAGIC", "에스케이매직"]),
    ("청호나이스", ["청호나이스", "청호"]),
    ("위닉스", ["위닉스", "WINIX"]),
    ("샤오미", ["샤오미", "XIAOMI"]),
    ("다이슨", ["다이슨", "DYSON"]),
    ("필립스", ["필립스", "PHILIPS"]),
    ("드롱기", ["드롱기", "DELONGHI"]),
    ("발뮤다", ["발뮤다", "BALMUDA"]),
    ("브라운", ["브라운", "BRAUN"]),
    ("일렉트로룩스", ["일렉트로룩스", "ELECTROLUX"]),
    ("캐리어", ["캐리어", "CARRIER"]),
    ("신일", ["신일", "SHINIL", "신일전자"]),
    ("한일", ["한일", "한일전기"]),
    ("휴롬", ["휴롬", "HUROM"]),
    ("바디프랜드", ["바디프랜드", "BODYFRIEND"]),
    ("코지마", ["코지마", "KOJIMA"]),
    ("세라젬", ["세라젬", "CERAGEM"]),
    ("쿠진아트", ["쿠진아트", "CUISINART"]),
    ("키친아트", ["키친아트", "KITCHENART"]),
]


def seed_brands() -> int:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    added = 0
    try:
        for name, aliases in COMPETITORS:
            if not db.scalar(select(Brand).where(Brand.name == name)):
                db.add(Brand(name=name, is_own=False, aliases_json=aliases))
                added += 1
        db.commit()
        print(f"[seed_brands] 경쟁 브랜드 {added}개 추가")
        return added
    finally:
        db.close()


if __name__ == "__main__":
    seed_brands()
