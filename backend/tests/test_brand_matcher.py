"""BrandMatcher 회귀 테스트 — 자사/경쟁사/부품 분류 정확도.

프로젝트 중 2회 발생한 매칭 회귀(경쟁사 오탐, recall 손실)를 방지한다.
독립 in-memory SQLite로 전역 엔진과 분리.
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Brand, Category, CuckooModel
from collector.brand_matcher import BrandMatcher


@pytest.fixture
def db():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    s = Session()
    s.add(Brand(name="쿠쿠", is_own=True, aliases_json=["쿠쿠", "CUCKOO", "쿠쿠전자", "쿠쿠홈시스"]))
    s.add(Brand(name="쿠첸", is_own=False, aliases_json=["쿠첸", "CUCHEN"]))
    s.add(Brand(name="코웨이", is_own=False, aliases_json=["코웨이", "COWAY"]))
    # 공식 카탈로그 샘플 (밥솥 본품 + 별매품)
    s.add(CuckooModel(model_code="CRP-AHF1010FD", base_code="CRP-AHF1010FD", product_group="IH전기압력밥솥", mapped_category_id=None, is_accessory=False))
    s.add(CuckooModel(model_code="CRP-ZHT0420FB", base_code="CRP-ZHT0420FB", product_group="별매품", mapped_category_id=None, is_accessory=True))
    s.commit()
    yield s
    s.close()


def test_catalog_exact_match_is_authoritative(db):
    # 공식 카탈로그 정확 매칭 → 최우선 자사(0.99), brand_raw 없어도
    m = BrandMatcher(db).match(brand_raw="", title="CUCKOO CRP-AHF1010FD(R) 화이트", category_name="전기밥솥")
    assert m.is_own and m.reason == "catalog" and m.confidence == 0.99


def test_catalog_accessory_flag(db):
    # 카탈로그 별매품 코드 → catalog_accessory True
    m = BrandMatcher(db).match(brand_raw="", title="쿠쿠 CRP-ZHT0420FB 내솥", category_name="전기밥솥")
    assert m.is_own and m.catalog_accessory is True


def test_cuckoo_brand_field_is_own(db):
    # 균형: brand_raw가 쿠쿠 제조사 별칭과 정확일치 → 카탈로그에 없어도 자사 인정.
    m = BrandMatcher(db).match(brand_raw="CUCKOO", title="CUCKOO CRP-EHB0310FW 화이트", category_name="전기밥솥")
    assert m.is_own and m.reason == "brand_field"


def test_competitor_brand_field_not_own(db):
    # 쿠첸 CIR-... : 코드 prefix는 인덕션이지만 brand_raw=쿠첸 → 자사 아님
    m = BrandMatcher(db).match(brand_raw="쿠첸", title="CIR-EB330TOB2", category_name="인덕션·전기레인지")
    assert not m.is_own
    assert m.reason == "brand_field"


def test_competitor_modelcode_not_misclassified(db):
    # 코웨이 CP-6201N : brand_raw=코웨이 → 모델코드 fallback 금지(자사 아님)
    m = BrandMatcher(db).match(brand_raw="코웨이", title="CP-6201N 자가관리", category_name="정수기")
    assert not m.is_own


def test_title_token_cuckoo_is_own(db):
    # 균형: 제목 첫 토큰이 정확히 '쿠쿠' → 자사(브랜드필드 없어도, 가스레인지 등 회복)
    m = BrandMatcher(db).match(brand_raw="", title="쿠쿠 스피드팟 멀티쿠커", category_name="멀티쿠커")
    assert m.is_own and m.reason == "title_brand"


def test_cuckoo_substring_brand_not_own(db):
    # '쿠쿠토이즈'·'쿠쿠스토어'처럼 첫토큰이 쿠쿠가 '포함'만 된 다른 브랜드는 자사 아님
    m = BrandMatcher(db).match(brand_raw="쿠쿠토이즈", title="쿠쿠토이즈 어린이 장난감", category_name="멀티쿠커")
    assert not m.is_own


def test_dirty_cuckoo_brand_without_title_not_own(db):
    # 타사 제품이 brand_raw='쿠쿠'로 더티하게 와도 제목에 쿠쿠 없으면 자사 아님(도루코 제모기 케이스)
    m = BrandMatcher(db).match(brand_raw="쿠쿠", title="도루코 샤이세이프 면도기 제모기날면도기", category_name="제모기")
    assert not m.is_own


def test_cuckoo_brand_with_title_is_own(db):
    # brand_raw=쿠쿠 + 제목에도 쿠쿠 → 자사 인정(정상 케이스)
    m = BrandMatcher(db).match(brand_raw="쿠쿠", title="쿠쿠 인스퓨어 가습기", category_name="가습기")
    assert m.is_own and m.reason == "brand_field"


def test_prefix_category_authority(db):
    # 카탈로그 미등록 쿠쿠라도 코드 prefix가 카탈로그상 단일 카테고리면 그 카테고리로 권위 부여
    af = Category(name="에어프라이어", level=2)
    db.add(af)
    db.flush()
    db.add_all([
        CuckooModel(model_code="CAF-A0810TW", base_code="CAF-A0810TW",
                    product_group="에어프라이어", mapped_category_id=af.id, is_accessory=False),
        CuckooModel(model_code="CAF-B0810TW", base_code="CAF-B0810TW",
                    product_group="에어프라이어", mapped_category_id=af.id, is_accessory=False),
    ])
    db.commit()
    m = BrandMatcher(db)  # 새 모델 반영 위해 재생성
    res = m.match(brand_raw="쿠쿠전자", title="쿠쿠전자 CUCKOO CAF-C9999 바스켓 튀김기", category_name="튀김기")
    assert res.is_own and res.catalog_category_id == af.id


def test_catalog_code_anywhere_in_title_is_own(db):
    # 카탈로그 코드가 제목 어디에 있든 자사 인정(브랜드명 없어도)
    m = BrandMatcher(db).match(brand_raw="", title="정품 가정용 CRP-AHF1010FD 내솥", category_name="전기밥솥")
    assert m.is_own and m.reason == "catalog"


def test_reseller_with_cuckoo_word_not_own(db):
    # '쿠쿠풍'처럼 제품명 속 쿠쿠 + 카탈로그 코드 없음 → 자사 아님
    m = BrandMatcher(db).match(brand_raw="", title="정품 정밀 가정용 쿠쿠풍 내솥", category_name="전기밥솥")
    assert not m.is_own


def test_noncatalog_code_no_brand_not_own(db):
    # 카탈로그에 없고 브랜드 신호(첫토큰·brand_raw)도 없으면 자사 아님(코드만으론 불인정)
    m = BrandMatcher(db).match(brand_raw="", title="CRP-DHP0610FW 화이트", category_name="전기밥솥")
    assert not m.is_own


def test_unknown_brand_not_own(db):
    m = BrandMatcher(db).match(brand_raw="키친아트", title="KRC-1004 화이트", category_name="전기밥솥")
    assert not m.is_own
    assert m.brand_id is None


def test_competitor_matched_via_brand_field(db):
    # 경쟁사는 brand_raw(구조화 필드)로 매칭
    m = BrandMatcher(db).match(brand_raw="쿠첸", title="쿠첸 전기밥솥", category_name="전기밥솥")
    assert not m.is_own and m.reason == "brand_field"


def test_competitor_leading_token_matched(db):
    # 제목 첫 토큰이 브랜드면 경쟁사도 매칭(삼성/LG 등 회복). 시작 앵커라 오탐 적음.
    m = BrandMatcher(db).match(brand_raw="", title="쿠첸 전기밥솥 압력", category_name="전기밥솥")
    assert not m.is_own and m.reason == "title_brand"
    assert m.brand_id is not None


def test_competitor_mid_title_not_matched(db):
    # 첫 토큰이 아닌 제목 '내부'엔 브랜드명이 없으면 매칭 안 함(오탐 방지).
    m = BrandMatcher(db).match(brand_raw="", title="가정용 미니 압력 밥솥", category_name="전기밥솥")
    assert m.brand_id is None and not m.is_own


def test_maker_field_recovers_line_name_brand(db):
    # brand에 미시드 라인명, maker에 시드 제조사 → maker로 매칭(삼성 김치플러스 케이스 모사).
    m = BrandMatcher(db).match(
        brand_raw="라인명없음", title="라인명없음 압력밥솥", category_name="전기밥솥",
        maker_raw="쿠첸",
    )
    assert not m.is_own and m.reason == "maker_field"
    assert m.brand_id is not None


def test_reseller_cuckoo_store_not_own(db):
    # 리셀러 'CUCKOO스토어' brand_raw는 자사 아님(자사는 정확일치만, substring 오탐 방지).
    m = BrandMatcher(db).match(brand_raw="CUCKOO스토어", title="CUCKOO스토어 고양이 캣타워", category_name="체온계")
    assert not m.is_own and m.brand_id is None


def test_second_token_cuckoo_not_own(db):
    # 제품명 속 2번째 토큰 'CUCKOO'는 자사로 오인하지 않음(첫 의미토큰만 신뢰).
    m = BrandMatcher(db).match(brand_raw="", title="만토 CUCKOO 휴대용 블루투스 스피커", category_name="블루투스스피커")
    assert not m.is_own


def test_is_strong_own_filter(db):
    # 자사 보조 검색 필터 — 카탈로그 또는 쿠쿠 제조사 정확일치만 True
    mt = BrandMatcher(db)
    assert mt.is_strong_own(brand_raw="CUCKOO", title="CUCKOO CK-XYZ999 미등록") is True  # brand 정확일치
    assert mt.is_strong_own(brand_raw="", title="CUCKOO CRP-AHF1010FD 화이트") is True   # 카탈로그
    assert mt.is_strong_own(brand_raw="CUCKOO스토어", title="고양이 캣타워") is False        # 리셀러
    assert mt.is_strong_own(brand_raw="", title="만토 CUCKOO 스피커") is False              # 제목 토큰뿐
