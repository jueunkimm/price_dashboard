"""네이버 데이터랩 통합검색어 트렌드 API 클라이언트(F7).

문서: https://developers.naver.com/docs/serviceapi/datalab/search/search.md
- 검색 OpenAPI와 동일한 Client ID/Secret 사용
- 카테고리 키워드의 상대 검색량(0~100) 시계열을 반환 → 수요 프록시
"""
from __future__ import annotations

import httpx

from app.config import settings

DATALAB_URL = "https://openapi.naver.com/v1/datalab/search"


class DatalabClient:
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

    def search_trend(
        self,
        keyword: str,
        start_date: str,
        end_date: str,
        time_unit: str = "date",
    ) -> list[dict]:
        """키워드의 상대 검색량 시계열. 반환: [{period, ratio}].

        start_date/end_date: 'YYYY-MM-DD', time_unit: date|week|month
        """
        body = {
            "startDate": start_date,
            "endDate": end_date,
            "timeUnit": time_unit,
            "keywordGroups": [{"groupName": keyword, "keywords": [keyword]}],
        }
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(DATALAB_URL, headers=self._headers(), json=body)
            resp.raise_for_status()
            data = resp.json()

        results = data.get("results", [])
        if not results:
            return []
        return [
            {"period": pt["period"], "ratio": pt["ratio"]}
            for pt in results[0].get("data", [])
        ]
