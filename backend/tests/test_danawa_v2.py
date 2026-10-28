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
