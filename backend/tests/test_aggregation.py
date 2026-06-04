"""집계 회귀 테스트 — 렌탈 월요금 오염가 차단.

네이버 가격비교 한 productId에 렌탈 오퍼가 끼면 제목에 '렌탈'이 없어도
lprice가 월요금(일시불가의 2~10%)으로 떨어져 트렌드가 비현실적으로 급락한다.
_daily_prices가 제품 최고가 대비 20% 미만 스냅샷을 제외하는지 검증한다.
"""
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import aggregation
from app.database import Base
from app.models import Brand, Category, PriceSnapshot, Product


def _snap(price: int, day: int):
    s = aggregation.PriceSnapshot(list_price=price)
    s.collected_at = datetime(2026, 6, day, 12, 0, tzinfo=timezone.utc)
    return s


def test_daily_prices_drops_rental_contamination():
    # 06-01 일시불 417,120 → 06-02 렌탈 월요금 16,900(4%)으로 오염
    snaps = [_snap(417_120, 1), _snap(16_900, 2)]
    daily = aggregation._daily_prices(snaps)
    prices = sorted(daily.values())
    assert 16_900 not in prices  # 렌탈 오염가 제외
    assert prices == [417_120]


def test_daily_prices_keeps_genuine_discount():
    # 정상 할인(30% off)은 보존 — 100,000 → 70,000
    snaps = [_snap(100_000, 1), _snap(70_000, 2)]
    daily = aggregation._daily_prices(snaps)
    assert sorted(daily.values()) == [70_000, 100_000]


def test_daily_prices_cheap_product_not_filtered():
    # 본래 저가 제품(최고가 자체가 낮음)은 자기 기준이라 아무것도 안 걸러짐
    snaps = [_snap(9_900, 1), _snap(8_500, 2)]
    daily = aggregation._daily_prices(snaps)
    assert sorted(daily.values()) == [8_500, 9_900]


def test_product_change_ignores_rental_crash():
    # 오염가가 current로 잡혀 -96% 가짜 급락이 나오지 않아야 한다
    snaps = [_snap(417_120, 1), _snap(16_900, 2)]
    ch = aggregation.product_change(snaps)
    assert ch["current_price"] == 417_120
    # 유효일이 하루뿐이므로 변동률은 None(가짜 급락 없음)
    assert ch["change_pct"] is None


@pytest.fixture
def db():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine)()
    yield s
    s.close()


def _dbsnap(product_id: int, price: int, day: int) -> PriceSnapshot:
    return PriceSnapshot(
        product_id=product_id,
        list_price=price,
        collected_at=datetime(2026, 6, day, 12, 0, tzinfo=timezone.utc),
    )


def test_has_own_lineup_is_data_driven(db):
    # ★(자사 라인업)은 정적 시드 플래그가 아니라 '실제 자사 매칭 ≥1건'으로 판정해야 한다.
    own = Brand(name="쿠쿠", is_own=True)
    rival = Brand(name="경쟁사", is_own=False)
    db.add_all([own, rival])
    db.flush()

    # A: 정적 플래그는 False지만 자사 제품이 실제로 있음 → ★ 여야 함
    cat_a = Category(name="냉장고", level=2, has_own_lineup=False)
    # B: 정적 플래그는 True지만 자사 제품이 없음 → ★ 아니어야 함
    cat_b = Category(name="TV", level=2, has_own_lineup=True)
    db.add_all([cat_a, cat_b])
    db.flush()

    pa = Product(category_id=cat_a.id, model_name="쿠쿠 냉장고", brand_id=own.id,
                 is_own_brand=True, is_accessory=False, is_rental=False)
    pb = Product(category_id=cat_b.id, model_name="경쟁 TV", brand_id=rival.id,
                 is_own_brand=False, is_accessory=False, is_rental=False)
    db.add_all([pa, pb])
    db.flush()
    db.add_all([_dbsnap(pa.id, 800_000, 1), _dbsnap(pb.id, 1_000_000, 1)])
    db.commit()

    res = {r["category_name"]: r["has_own_lineup"] for r in aggregation.category_overview(db)}
    assert res["냉장고"] is True   # 자사 제품 존재 → 정적 False 무시하고 ★
    assert res["TV"] is False      # 자사 제품 없음 → 정적 True 무시하고 ★ 제거


def test_has_own_lineup_ignores_accessory_only(db):
    # 자사 매칭이 부품(액세서리)뿐이면 라인업으로 치지 않는다.
    own = Brand(name="쿠쿠", is_own=True)
    db.add(own)
    db.flush()
    cat = Category(name="전기밥솥", level=2, has_own_lineup=False)
    db.add(cat)
    db.flush()
    acc = Product(category_id=cat.id, model_name="쿠쿠 내솥", brand_id=own.id,
                  is_own_brand=True, is_accessory=True, is_rental=False)
    db.add(acc)
    db.flush()
    db.add(_dbsnap(acc.id, 30_000, 1))
    db.commit()

    res = {r["category_name"]: r["has_own_lineup"] for r in aggregation.category_overview(db)}
    # 부품만 있으면 본품 라인업 아님(애초에 집계 풀에서도 제외되어 결과 미포함이면 통과)
    assert res.get("전기밥솥", False) is False
