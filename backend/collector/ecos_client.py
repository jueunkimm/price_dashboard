"""한국은행 ECOS API 클라이언트(F12) — 환율 등 거시지표.

문서: https://ecos.bok.or.kr/api/
- 별도 ECOS 인증키 필요(.env: ECOS_API_KEY). 키 미설정 시 사용 불가.
- USD/KRW 등 일자별 시계열 반환.
"""
from __future__ import annotations

import httpx

from app.config import settings

ECOS_BASE = "https://ecos.bok.or.kr/api/StatisticSearch"


class EcosClient:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.ecos_api_key
        if not self.api_key:
            raise RuntimeError(
                "ECOS_API_KEY 가 .env에 설정되지 않았습니다. "
                "https://ecos.bok.or.kr/api 에서 발급 후 추가하세요."
            )

    def usd_krw(self, start: str, end: str) -> list[dict]:
        """원/달러 환율 일별 시계열. start/end: 'YYYYMMDD'.

        통계표 731Y001(주요국 통화의 대원화환율), 항목 0000001(미국 달러).
        """
        url = (
            f"{ECOS_BASE}/{self.api_key}/json/kr/1/1000/"
            f"731Y001/D/{start}/{end}/0000001"
        )
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(url)
            resp.raise_for_status()
            data = resp.json()
        rows = data.get("StatisticSearch", {}).get("row", [])
        out = []
        for r in rows:
            try:
                out.append({"period": r["TIME"], "value": float(r["DATA_VALUE"])})
            except (KeyError, ValueError):
                continue
        return out
