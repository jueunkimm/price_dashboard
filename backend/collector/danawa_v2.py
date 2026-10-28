"""다나와(Next.js 개편판) 파서 v2 — 가격 수집의 신규 원천.

배경: 네이버 쇼핑 검색 API가 2026-07-31 종료(대체 없음)되어 가격 수집 소스를
다나와로 전환(docs/재설계안_v2.md). 다나와 신규 프론트는 RSC(__next_f) 페이로드에
구조화 JSON을 내장하므로, 브라우저 없이 httpx + 문자열 파싱으로 수집한다.

제공 함수:
- category_products(cate, page): 카테고리 목록의 카탈로그 상품(모델 단위, 최저가 포함)
- search_products(query): 통합검색의 카탈로그 상품(가격비교 항목, productSeq=pcode)
- search_offers(query): 통합검색의 몰별 오퍼(카탈로그 미등록 모델 폴백용)

주의: 파서는 다나와 구조 변경에 민감 — 수집기는 '0건=실패'로 다뤄
기존 데이터를 빈 결과로 덮지 않는다(재설계안 §3 안정장치).
"""
from __future__ import annotations

import html as _html
import json
import re
import time

import httpx

UA = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/130.0 Safari/537.36"
    )
}
REQUEST_INTERVAL = 1.2  # 초 — 저부하 수집(일 2회 cron 기준 전체 10~15분)
_last_request = 0.0


def _throttle() -> None:
    global _last_request
    wait = REQUEST_INTERVAL - (time.monotonic() - _last_request)
    if wait > 0:
        time.sleep(wait)
    _last_request = time.monotonic()


def _fetch(url: str, retries: int = 2) -> str:
    last_err: Exception | None = None
    for attempt in range(retries + 1):
        try:
            _throttle()
            r = httpx.get(url, timeout=20.0, follow_redirects=True, headers=UA)
            r.raise_for_status()
            return r.text
        except Exception as e:  # noqa: BLE001 — 재시도 후 상위에서 집계
            last_err = e
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"다나와 요청 실패: {url} — {last_err}")


def _rsc_blob(page_html: str) -> str:
    """Next.js RSC 페이로드(self.__next_f.push)를 모아 JS 문자열 이스케이프 해제."""
    chunks = re.findall(r'self\.__next_f\.push\(\[1,\s*"((?:[^"\\]|\\.)*)"\]\)', page_html)
    blob = "".join(chunks)
    # JS 문자열 리터럴 해제: \uXXXX·\" 등. latin-1 round-trip으로 비ASCII 보존.
    return (
        blob.encode("utf-8")
        .decode("unicode_escape")
        .encode("latin-1", errors="ignore")
        .decode("utf-8", errors="ignore")
    )


def _extract_objects(blob: str, must_have: tuple[str, ...], max_len: int = 25000) -> list[dict]:
    """문자열 인식 브레이스 매칭으로 must_have 키를 모두 가진 '최소' JSON 오브젝트 추출."""
    out: list[dict] = []
    seen_ids: set[str] = set()
    stack: list[int] = []
    in_str = esc = False
    for i, c in enumerate(blob):
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
            continue
        if c == '"':
            in_str = True
        elif c == "{":
            stack.append(i)
        elif c == "}":
            if not stack:
                continue
            s = stack.pop()
            if i - s > max_len:
                continue
            seg = blob[s : i + 1]
            if not all(k in seg for k in must_have):
                continue
            try:
                obj = json.loads(seg)
            except json.JSONDecodeError:
                continue
            # 식별자 기준 중복 제거(최소 오브젝트 우선)
            oid = str(obj.get("id") or obj.get("productSeq") or "")
            if not oid or oid in seen_ids:
                continue
            seen_ids.add(oid)
            out.append(obj)
    return out


def _clean(text: str | None) -> str:
    """HTML 엔티티 해제 후 태그(<b> 등) 제거 — 순서 중요(&lt;b&gt; → <b> → 제거)."""
    if not text:
        return ""
    return re.sub(r"<[^>]+>", "", _html.unescape(text)).strip()


def _spec_text(obj: dict) -> str:
    """descriptionSegments/summary.desc → '스팀다리미 / 용량: 95mL …' 형태 스펙 문자열."""
    segs = obj.get("descriptionSegments") or []
    if segs:
        parts = []
        for s in segs:
            t = (s or {}).get("text") or ""
            if t:
                parts.append(t)
        return " / ".join(parts)[:500]
    summary = (obj.get("summary") or {}).get("desc") or []
    return " / ".join(str(x) for x in summary)[:500]


# ───────────────────── Track A: 카테고리 목록 ─────────────────────

def category_products(cate: str | int, page: int = 1) -> list[dict]:
    """카테고리 목록 페이지의 카탈로그 상품(약 31개/페이지, 인기순 BEST)."""
    url = f"https://prod.danawa.com/list/?cate={cate}&page={page}"
    blob = _rsc_blob(_fetch(url))
    objs = _extract_objects(blob, must_have=('"productUrl"', '"price":{"min"'))
    items = []
    for o in objs:
        price = ((o.get("price") or {}).get("min")) or 0
        m = re.search(r"pcode=(\d+)", o.get("productUrl") or "")
        if not m or price <= 0:
            continue
        cat = o.get("category") or {}
        stats = o.get("stats") or {}
        items.append(
            {
                "pcode": m.group(1),
                "title": _clean(o.get("productName")),
                "model_name_part": _clean(o.get("modelName")),
                "maker": _clean(o.get("makerName")),
                "brand": _clean(o.get("brandName")),
                "price": int(price),
                "spec_text": _spec_text(o),
                "cate_names": (cat.get("names") or []),
                "shop_count": (stats.get("shopCount") or 0),
                "hit_rank": o.get("hitRank"),
                "image": ((o.get("image") or {}).get("url") or "")[:500],
                "url": (o.get("productUrl") or "")[:500],
                "register_date": o.get("registerDate") or "",
            }
        )
    return items


# ───────────────────── Track B: 통합검색 ─────────────────────

def search_products(query: str) -> list[dict]:
    """통합검색의 가격비교(카탈로그) 상품 — productSeq=pcode, minPrice=최저가."""
    url = f"https://search.danawa.com/?query={httpx.QueryParams({'q': query})['q']}"
    blob = _rsc_blob(_fetch(url))
    objs = _extract_objects(blob, must_have=('"productSeq"', '"minPrice"'))
    items = []
    for o in objs:
        price = o.get("minPrice") or o.get("minPriceNumber") or 0
        try:
            price = int(price)
        except (TypeError, ValueError):
            continue
        if price <= 0 or not o.get("productSeq"):
            continue
        seq = str(o.get("productSeq"))
        # 검색결과에는 두 종류가 섞여 있다:
        #  - 카탈로그(prodType=1): 숫자 pcode, info?pcode= 상세 페이지가 열림
        #  - 몰 리스팅(prodType=3 등): 'EE128_3964263358' 같은 몰 상품코드. info?pcode=에 넣으면
        #    다나와가 "잘못된 접근입니다"를 띄우므로, 원본 linkUrl(go_link_goods 연결 링크)을 써야 한다.
        is_catalog = seq.isdigit()
        link_url = o.get("linkUrl") or ""
        url = f"https://prod.danawa.com/info/?pcode={seq}" if is_catalog else link_url
        items.append(
            {
                "pcode": seq,
                "is_catalog": is_catalog,
                "title": _clean(o.get("productName")),
                "maker": _clean(o.get("makerName")),
                "brand": _clean(o.get("brandName")),
                "price": price,
                "spec_text": _spec_text(o),
                "url": url[:500],
            }
        )
    return items


def search_offers(query: str) -> list[dict]:
    """통합검색의 몰별 오퍼(HTML 카드) — 카탈로그 미등록 모델의 폴백.

    카드 하나가 여러 anchor(이미지/제목/가격)로 나뉘므로 link_prod_c로 그룹핑.
    """
    page_html = _fetch(f"https://search.danawa.com/?query={httpx.QueryParams({'q': query})['q']}")
    parts = re.split(r"(?=<a[^>]+bridge/go_link_goods)", page_html)
    groups: dict[str, dict] = {}
    order: list[str] = []
    for seg in parts[1:]:
        seg = seg[:4000]
        href_m = re.search(r'href="([^"]+go_link_goods[^"]*)"', seg)
        if not href_m:
            continue
        href = _html.unescape(href_m.group(1))
        prod_m = re.search(r"link_prod_c=(\d+)", href)
        if not prod_m:
            continue
        key = prod_m.group(1)
        g = groups.get(key)
        if g is None:
            mall = re.search(r"cmpny_c=([A-Z0-9]+)", href)
            cate = re.search(r"[?&]cate=(\d+)", href)
            g = groups[key] = {
                "link_prod_c": key,
                "mall_code": mall.group(1) if mall else None,
                "cate": cate.group(1) if cate else None,
                "link": href[:500],
                "name": None,
                "price": None,
            }
            order.append(key)
        if not g["name"]:
            alt = re.search(r'alt="([^"]{6,150})"', seg)
            if alt:
                g["name"] = _clean(alt.group(1))
        if not g["price"]:
            pr = re.search(r">\s*([\d]{1,3}(?:,\d{3})+)\s*<", seg)
            if pr:
                try:
                    g["price"] = int(pr.group(1).replace(",", ""))
                except ValueError:
                    pass
    return [groups[k] for k in order if groups[k]["name"] and groups[k]["price"]]


if __name__ == "__main__":
    import io
    import sys

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    mode = sys.argv[1] if len(sys.argv) > 1 else "cate"
    arg = sys.argv[2] if len(sys.argv) > 2 else ("10325673" if mode == "cate" else "CRP-FHTS0610FB")
    if mode == "cate":
        rows = category_products(arg)
        print(f"[danawa_v2] cate={arg} → {len(rows)}개")
        for r in rows[:5]:
            print(f"  ₩{r['price']:>9,} 몰{r['shop_count']:>3} {r['title'][:36]} | {r['spec_text'][:40]}")
    elif mode == "search":
        rows = search_products(arg)
        print(f"[danawa_v2] search={arg} → 카탈로그 {len(rows)}개")
        for r in rows[:5]:
            print(f"  ₩{r['price']:>9,} {r['title'][:40]} | {r['maker']}")
    else:
        rows = search_offers(arg)
        print(f"[danawa_v2] offers={arg} → {len(rows)}개")
        for r in rows[:5]:
            print(f"  ₩{(r['price'] or 0):>9,} [{r['mall_code']}] {(r['name'] or '')[:40]}")
