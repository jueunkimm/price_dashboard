"""네이버쇼핑 검색 API 클라이언트.

문서: https://developers.naver.com/docs/serviceapi/search/shopping/shopping.md
- 합법/안정 공식 OpenAPI 우선(기획서 5.2)
- rate limit 준수, User-Agent 명시
"""
from __future__ import annotations

import html
import re

import httpx

from app.config import settings

SHOP_URL = "https://openapi.naver.com/v1/search/shop.json"
_TAG_RE = re.compile(r"<[^>]+>")


def _clean(text: str) -> str:
    """네이버가 검색어에 붙이는 <b> 태그/HTML 엔티티 제거."""
    return html.unescape(_TAG_RE.sub("", text or "")).strip()


class NaverShopClient:
    def __init__(self, client_id: str | None = None, client_secret: str | None = None):
        self.client_id = client_id or settings.naver_client_id
        self.client_secret = client_secret or settings.naver_client_secret
        if not self.client_id or not self.client_secret:
            raise RuntimeError("NAVER_CLIENT_ID / NAVER_CLIENT_SECRET 가 .env에 설정되지 않았습니다.")

    def _headers(self) -> dict[str, str]:
        return {
            "X-Naver-Client-Id": self.client_id,
            "X-Naver-Client-Secret": self.client_secret,
            "User-Agent": "price-dashboard/0.1 (+research; contact:admin@example.com)",
        }

    def search(self, query: str, display: int = 50, sort: str = "sim") -> list[dict]:
        """상품 검색. 반환: 정규화된 dict 리스트.

        sort: sim(정확도) | date | asc(가격오름) | dsc(가격내림)
        """
        params = {"query": query, "display": min(display, 100), "sort": sort}
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(SHOP_URL, headers=self._headers(), params=params)
            resp.raise_for_status()
            data = resp.json()

        items: list[dict] = []
        for it in data.get("items", []):
            try:
                price = int(it.get("lprice") or 0)
            except (TypeError, ValueError):
                price = 0
            if price <= 0:
                continue
            items.append(
                {
                    "external_id": it.get("productId"),
                    "title": _clean(it.get("title", "")),
                    "brand_raw": _clean(it.get("brand") or it.get("maker") or ""),
                    "price": price,
                    "mall": _clean(it.get("mallName", "")),
                    "link": it.get("link", ""),
                    "category": _clean(it.get("category3") or it.get("category2") or ""),
                    # 네이버 세부분류(category4): 드럼세탁기·의류건조기·냉온정수기 등
                    "sub_category": _clean(it.get("category4") or it.get("category3") or ""),
                }
            )
        return items
