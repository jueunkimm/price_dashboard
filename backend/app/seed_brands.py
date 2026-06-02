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
    # 삼성/LG는 네이버 brand_raw에 라인명(비스포크·디오스 등)이 들어오므로 별칭으로 흡수
    ("삼성전자", ["삼성", "SAMSUNG", "삼성전자", "비스포크", "BESPOKE", "그랑데", "셰프컬렉션"]),
    ("LG전자", [
        "LG", "엘지", "LG전자", "LG ELECTRONICS",
        "디오스", "DIOS", "트롬", "TROMM", "오브제", "오브제컬렉션", "OBJET",
        "스타일러", "STYLER", "휘센", "WHISEN", "통돌이", "코드제로", "퓨리케어", "틔운",
    ]),
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
    # 2차 보강 — 미매칭(기타/미상) 상위 실브랜드
    ("미닉스", ["미닉스", "MINIX"]),
    ("닌자", ["닌자", "NINJA"]),
    ("로보락", ["로보락", "ROBOROCK"]),
    ("브리타", ["브리타", "BRITA"]),
    ("나비엔", ["나비엔", "NAVIEN", "나비엔매직"]),
    ("이누스", ["이누스", "INUS"]),
    ("한경희", ["한경희", "한경희생활과학"]),
    ("에브리봇", ["에브리봇", "EVERYBOT"]),
    ("매직쉐프", ["매직쉐프", "MAGIC CHEF", "MAGICCHEF"]),
    ("린나이", ["린나이", "RINNAI"]),
    ("테팔", ["테팔", "TEFAL"]),
    ("네스프레소", ["네스프레소", "NESPRESSO"]),
    ("드리미", ["드리미", "DREAME"]),
    ("파나소닉", ["파나소닉", "PANASONIC"]),
    ("파세코", ["파세코", "PASECO"]),
    ("콘에어", ["콘에어", "CONAIR"]),
    ("아이닉", ["아이닉", "AINIC"]),
    ("보국전자", ["보국전자", "보국"]),
    ("카스", ["카스", "CAS"]),
    ("쿠잉", ["쿠잉", "CUING"]),
    # 3차 보강 — 인지도 높은 미매칭 브랜드
    ("샤크", ["샤크", "SHARK"]),
    ("오아", ["오아"]),
    ("노비타", ["노비타", "NOVITA"]),
    ("인바디", ["인바디", "INBODY"]),
    ("에코백스", ["에코백스", "ECOVACS"]),
    ("브레빌", ["브레빌", "BREVILLE"]),
    ("보스", ["BOSE", "보스"]),
    ("유닉스", ["유닉스", "UNIX"]),
    ("엡손", ["엡손", "EPSON"]),
    ("뷰소닉", ["뷰소닉", "VIEWSONIC"]),
    ("엑스지미", ["엑스지미", "XGIMI"]),
    ("루메나", ["루메나", "LUMENA"]),
    ("JMW", ["JMW"]),
    ("보만", ["보만", "BOMANN"]),
    ("듀플렉스", ["듀플렉스", "DUPLEX"]),
    ("JBL", ["JBL"]),
    ("대림바스", ["대림바스", "대림"]),
]


def seed_brands() -> int:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    added = 0
    updated = 0
    try:
        for name, aliases in COMPETITORS:
            b = db.scalar(select(Brand).where(Brand.name == name))
            if not b:
                db.add(Brand(name=name, is_own=False, aliases_json=aliases))
                added += 1
            elif (b.aliases_json or []) != aliases:
                b.aliases_json = aliases  # 별칭 변경 시 갱신(라인명 추가 등)
                updated += 1
        db.commit()
        print(f"[seed_brands] 경쟁 브랜드 {added}개 추가 / {updated}개 별칭 갱신")
        return added
    finally:
        db.close()


if __name__ == "__main__":
    seed_brands()
