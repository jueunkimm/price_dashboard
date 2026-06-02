"""BrandMatcher 회귀 테스트 — 자사/경쟁사/부품 분류 정확도.

프로젝트 중 2회 발생한 매칭 회귀(경쟁사 오탐, recall 손실)를 방지한다.
독립 in-memory SQLite로 전역 엔진과 분리.
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Brand, CuckooModel
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


def test_brand_field_cuckoo(db):
    m = BrandMatcher(db).match(brand_raw="CUCKOO", title="CRP-EHB0310FW 화이트", category_name="전기밥솥")
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


def test_title_token_cuckoo_no_brandfield(db):
    # brand_raw 비고 제목에 쿠쿠 → 자사(recall 보존)
    m = BrandMatcher(db).match(brand_raw="", title="쿠쿠 스피드팟 멀티쿠커", category_name="멀티쿠커")
    assert m.is_own and m.reason == "title"


def test_modelcode_only_empty_brand(db):
    # brand_raw 비고 토큰도 없지만 카테고리 부합 모델코드 → 자사(방법 B)
    m = BrandMatcher(db).match(brand_raw="", title="CRP-DHP0610FW 화이트", category_name="전기밥솥")
    assert m.is_own and m.reason == "modelcode+category"


def test_unknown_brand_not_own(db):
    m = BrandMatcher(db).match(brand_raw="키친아트", title="KRC-1004 화이트", category_name="전기밥솥")
    assert not m.is_own
    assert m.brand_id is None


def test_competitor_matched_via_brand_field(db):
    # 경쟁사는 brand_raw(구조화 필드)로 매칭
    m = BrandMatcher(db).match(brand_raw="쿠첸", title="쿠첸 전기밥솥", category_name="전기밥솥")
    assert not m.is_own and m.reason == "brand_field"


def test_competitor_title_only_not_matched(db):
    # 경쟁사는 제목만으로는 매칭 안 함(오탐 방지) — brand_raw 비면 미상
    m = BrandMatcher(db).match(brand_raw="", title="쿠첸 전기밥솥 압력", category_name="전기밥솥")
    assert m.brand_id is None and not m.is_own
