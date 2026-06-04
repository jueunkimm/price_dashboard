"""집계 회귀 테스트 — 렌탈 월요금 오염가 차단.

네이버 가격비교 한 productId에 렌탈 오퍼가 끼면 제목에 '렌탈'이 없어도
lprice가 월요금(일시불가의 2~10%)으로 떨어져 트렌드가 비현실적으로 급락한다.
_daily_prices가 제품 최고가 대비 20% 미만 스냅샷을 제외하는지 검증한다.
"""
from datetime import datetime, timezone

from app import aggregation


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
