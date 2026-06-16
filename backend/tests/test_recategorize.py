"""recategorize 회귀 테스트 — 네이버분류 소유권 기반 자동 카테고리 교정.

검증:
  1) 다른 카테고리가 '소유'한 네이버분류를 가진 오배치 제품은 그 카테고리로 이동.
  2) 어느 카테고리도 대표가 아닌 네이버분류(잡화)는 이동되지 않음.
  3) 지금 카테고리에 정배치된 제품(대표분류 일치)은 손대지 않음.
  4) 같은 네이버분류를 여러 카테고리가 공유(모호)하면 라우팅하지 않음.
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Category, Product
from collector import recategorize as rc


@pytest.fixture
def session(monkeypatch):
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    SL = sessionmaker(bind=engine)
    monkeypatch.setattr(rc, "SessionLocal", SL)
    return SL


def _p(cat, nc, name):
    return Product(category_id=cat, naver_cat=nc, model_name=name,
                   is_rental=False, is_accessory=False)


def test_routes_misplaced_and_protects_junk_and_correct(session):
    db = session()
    db.add_all([Category(id=1, name="가스오븐레인지"),
                Category(id=2, name="전자레인지·오븐"),
                Category(id=3, name="와인셀러")])
    rows = []
    # cat1 대표 = '가스레인지'(표본 5)
    rows += [_p(1, "가스레인지", f"가스 오븐레인지 {i}") for i in range(5)]
    # cat2 대표 = '전기레인지/인덕션'(표본 5)
    rows += [_p(2, "전기레인지/인덕션", f"전기 오븐 {i}") for i in range(5)]
    # cat3 대표 = '와인셀러'(표본 5)
    rows += [_p(3, "와인셀러", f"와인냉장고 {i}") for i in range(5)]
    # (1) 오배치: cat1에 있지만 네이버분류는 cat2 소유 → cat2로 이동되어야
    misplaced = _p(1, "전기레인지/인덕션", "쿠쿠 전기 광파오븐 CMW")
    rows.append(misplaced)
    # (2) 잡화: 어느 카테고리도 대표 아님 → 이동 안 됨(cat3 유지)
    junk = _p(3, "와인용품/디캔터", "위스키 디캔터 300ml 잡화")
    rows.append(junk)
    # (3) 정배치: cat2 대표분류 일치 → 손대지 않음
    correct = _p(2, "전기레인지/인덕션", "정배치 전기오븐")
    rows.append(correct)
    db.add_all(rows)
    db.commit()

    res = rc.recategorize()

    db2 = session()
    assert db2.get(Product, misplaced.id).category_id == 2  # (1) 이동
    assert db2.get(Product, junk.id).category_id == 3        # (2) 유지
    assert db2.get(Product, correct.id).category_id == 2     # (3) 유지
    assert res["moves"] == 1


def test_ambiguous_navercat_not_routed(session):
    db = session()
    db.add_all([Category(id=1, name="A"), Category(id=2, name="B"), Category(id=3, name="C")])
    rows = []
    # 같은 네이버분류 '주방가전'이 cat1·cat2 둘 다 대표 → 모호 → 소유자 없음
    rows += [_p(1, "주방가전", f"a{i}") for i in range(5)]
    rows += [_p(2, "주방가전", f"b{i}") for i in range(5)]
    rows += [_p(3, "정수기", f"c{i}") for i in range(5)]
    # cat3에 '주방가전' 제품 하나 — 모호 분류라 이동되면 안 됨
    amb = _p(3, "주방가전", "모호분류 제품")
    rows.append(amb)
    db.add_all(rows)
    db.commit()

    res = rc.recategorize()
    assert session().get(Product, amb.id).category_id == 3  # 모호 → 유지
    assert res["moves"] == 0
