"""네이버 데이터랩 쇼핑인사이트 — 키워드별 쇼핑 클릭 추이(F7 보강).

검색어트렌드(통합검색)와 달리 **네이버쇼핑 내 클릭** 추이라 구매의도에 더 가깝다.
키워드별 트렌드 API는 (광범위 분야 cid + 키워드) 조합으로 조회한다.
문서: https://developers.naver.com/docs/serviceapi/datalab/shopping/shopping.md
"""
from __future__ import annotations

import httpx

from app.config import settings

KEYWORDS_URL = "https://openapi.naver.com/v1/datalab/shopping/category/keywords"

# 네이버쇼핑 분야 cid
CID_DIGITAL = "50000003"  # 디지털/가전
CID_LIVING = "50000008"  # 생활/건강

# 카테고리 → cid (기본은 디지털/가전, 생활/건강이 더 맞는 것만 override)
CATEGORY_CID: dict[str, str] = {
    "비데": CID_LIVING,
    "정수기": CID_LIVING,
    "안마의자·안마기": CID_LIVING,
    "체중계": CID_LIVING,
}


def cid_for(category_name: str | None) -> str:
    return CATEGORY_CID.get(category_name or "", CID_DIGITAL)


class ShoppingInsightClient:
    def __init__(self, client_id: str | None = None, client_secret: str | None = None):
        self.client_id = client_id or settings.naver_client_id
        self.client_secret = client_secret or settings.naver_client_secret
        if not self.client_id or not self.client_secret:
            raise RuntimeError("NAVER_CLIENT_ID / NAVER_CLIENT_SECRET 가 설정되지 않았습니다.")

    def _headers(self) -> dict[str, str]:
        return {
            "X-Naver-Client-Id": self.client_id,
            "X-Naver-Client-Secret": self.client_secret,
            "Content-Type": "application/json",
        }

    def keyword_trend(
        self,
        keyword: str,
        cid: str,
        start_date: str,
        end_date: str,
        time_unit: str = "date",
    ) -> list[dict]:
        """분야(cid) 내 키워드의 쇼핑 클릭 추이. 반환: [{period, ratio}]."""
        body = {
            "startDate": start_date,
            "endDate": end_date,
            "timeUnit": time_unit,
            "category": cid,
            "keyword": [{"name": keyword, "param": [keyword]}],
            "device": "",
            "gender": "",
            "ages": [],
        }
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(KEYWORDS_URL, headers=self._headers(), json=body)
            resp.raise_for_status()
            data = resp.json()
        results = data.get("results", [])
        if not results:
            return []
        return [
            {"period": pt["period"], "ratio": pt["ratio"]}
            for pt in results[0].get("data", [])
        ]
