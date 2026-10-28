"""다나와 v2 파서 회귀 테스트 — 네트워크 없이 고정 픽스처로 핵심 로직 보호."""
from collector.danawa_v2 import _clean, _extract_objects, _rsc_blob


class TestClean:
    def test_entity_then_tag(self):
        # &lt;b&gt; → <b> → 제거 (순서가 바뀌면 '<b>'가 남는 회귀)
        assert _clean("쿠쿠 &lt;b&gt;CSI-D300W&lt;/b&gt; 다리미") == "쿠쿠 CSI-D300W 다리미"

    def test_plain(self):
        assert _clean("  니카사 시즌2  ") == "니카사 시즌2"
        assert _clean(None) == ""


class TestRscBlob:
    def test_unescape(self):
        html = r'<script>self.__next_f.push([1,"{\"price\":{\"min\":162360},\"name\":\"스팀\"}"])</script>'
        blob = _rsc_blob(html)
        assert '"min":162360' in blob
        assert "스팀" in blob


class TestExtractObjects:
    BLOB = (
        'junk{"id":1,"other":true}mid'
        '{"id":"122691190","productUrl":"https://prod.danawa.com/info/?pcode=122691190",'
        '"price":{"min":162360,"total":162360},"productName":"니카사 시즌2"}'
        '{"id":"99","productUrl":"https://prod.danawa.com/info/?pcode=99",'
        '"price":{"min":5000},"productName":"브라켓"}'
    )

    def test_extracts_matching_objects_only(self):
        objs = _extract_objects(self.BLOB, must_have=('"productUrl"', '"price":{"min"'))
        assert len(objs) == 2
        assert objs[0]["price"]["min"] == 162360
        assert objs[0]["productName"] == "니카사 시즌2"

    def test_dedup_by_id(self):
        objs = _extract_objects(self.BLOB + self.BLOB, must_have=('"productUrl"', '"price":{"min"'))
        assert len(objs) == 2  # 동일 id 중복 제거

    def test_string_aware_braces(self):
        # 문자열 안의 중괄호가 매칭을 깨지 않아야 함
        blob = '{"id":"7","productUrl":"x?pcode=7","price":{"min":10},"name":"브레이스 { } 포함"}'
        objs = _extract_objects(blob, must_have=('"productUrl"', '"price":{"min"'))
        assert len(objs) == 1 and objs[0]["name"] == "브레이스 { } 포함"


class TestLinkSafety:
    """몰 상품코드(EE128_…)로 만든 info?pcode= 링크는 '잘못된 접근입니다'가 뜬다."""

    def test_export_sanitizes_mall_code_link(self):
        from app.export_static import _safe_link

        bad = "https://prod.danawa.com/info/?pcode=TYB19C_13746654684"
        fixed = _safe_link(bad, "CSD-AHA110LW", "쿠쿠 리네이처 메디킨하이")
        assert "pcode=" not in fixed
        assert fixed.startswith("https://search.danawa.com/?query=CSD-AHA110LW")

    def test_export_keeps_valid_links(self):
        from app.export_static import _safe_link

        ok = "https://prod.danawa.com/info/?pcode=92660366&cate=1"
        assert _safe_link(ok, "X", "y") == ok
        bridge = "https://prod.danawa.com/bridge/go_link_goods.php?cmpny_c=TZ6171&link_prod_c=1"
        assert _safe_link(bridge, "X", "y") == bridge
        assert _safe_link(None, "X", "y") is None

    def test_pick_catalog_ignores_mall_listings(self):
        from collector.collect_danawa_own import _pick_catalog

        items = [
            {"title": "쿠쿠 리네이처 CSD-AHA110LW", "price": 1557700, "maker": "쿠쿠", "is_catalog": True},
            {"title": "쿠쿠홈시스 쿠쿠 CSD-AHA110LW 몰판매", "price": 1600000, "maker": "쿠쿠", "is_catalog": False},
        ]
        best = _pick_catalog("CSD-AHA110LW", items)
        assert best["is_catalog"] is True and best["price"] == 1557700

    def test_pick_catalog_none_when_only_mall_listings(self):
        from collector.collect_danawa_own import _pick_catalog

        items = [{"title": "쿠쿠 CSD-AHA110LW", "price": 1, "maker": "쿠쿠", "is_catalog": False}]
        assert _pick_catalog("CSD-AHA110LW", items) is None  # → 몰 오퍼 폴백으로 넘어감


class TestPurge:
    def test_purge_removes_only_mall_code_products(self):
        from sqlalchemy import create_engine, select
        from sqlalchemy.orm import sessionmaker

        from app.database import Base
        from app.models import Category, PriceSnapshot, Product
        from collector.collect_danawa_own import purge_broken_mall_products

        eng = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(eng)
        db = sessionmaker(bind=eng)()
        cat = Category(name="c", level=2)
        db.add(cat)
        db.flush()
        keep_ids = ["danawa:92660366", "danawa:offer-CSD-AHA110LW", "naver:123"]
        for ext in keep_ids + ["danawa:EE128_3964263358", "danawa:TYB19C_13746654684"]:
            p = Product(category_id=cat.id, external_id=ext, model_name=ext)
            db.add(p)
            db.flush()
            db.add(PriceSnapshot(product_id=p.id, list_price=100))
        db.commit()

        assert purge_broken_mall_products(db) == 2
        left = sorted(db.scalars(select(Product.external_id)).all())
        assert left == sorted(keep_ids)
        # 삭제된 제품의 이력도 함께 정리(고아 스냅샷 없음)
        assert len(db.scalars(select(PriceSnapshot)).all()) == 3
        assert purge_broken_mall_products(db) == 0  # 멱등
