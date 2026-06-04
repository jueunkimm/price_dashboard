"""브랜드 매칭(F-C 핵심) — 수집 원문에서 자사(쿠쿠) 여부 판별.

정확도 보강(방법 A+): 오탐(false positive) 제거를 위해 2단계 신뢰도로 판별.
  1) 구조화된 브랜드 필드(brand_raw) 매칭 → 강한 신호 (쿠첸/CUCHEN 등 유사 브랜드 자동 배제)
  2) 제목(title) 기반 매칭은 "쿠쿠/CUCKOO 토큰 + 쿠쿠 모델코드 패턴"이 함께 있을 때만 인정

근거: 쿠쿠 모델코드는 'C' + 1~3 알파벳 + 하이픈 + 3~4 숫자 형태(CRP-1010, CMC-..., CP-..., CBT-... 등).
추후 실제 모델 리스트(방법 B)를 brand 시드에 추가하면 정확도를 더 높일 수 있음.
"""
from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.cuckoo_catalog import normalize_code
from app.models import Brand, CuckooModel

# 제목에서 모델코드 토큰 추출
_CODE_TOKEN_RE = re.compile(r"\b([A-Z]{2,5}-[A-Z0-9]{3,})")


def _normalize(text: str) -> str:
    return (text or "").lower().replace(" ", "")


class MatchResult:
    __slots__ = ("brand_id", "is_own", "confidence", "reason", "catalog_category_id", "catalog_accessory")

    def __init__(
        self,
        brand_id: int | None,
        is_own: bool,
        confidence: float,
        reason: str,
        catalog_category_id: int | None = None,
        catalog_accessory: bool = False,
    ):
        self.brand_id = brand_id
        self.is_own = is_own
        self.confidence = confidence
        self.reason = reason
        self.catalog_category_id = catalog_category_id  # 공식 카탈로그 권위 카테고리
        self.catalog_accessory = catalog_accessory  # 공식 카탈로그 별매품 여부


class BrandMatcher:
    """공식 카탈로그(최우선) + brand.aliases_json 기반 매칭."""

    def __init__(self, db: Session):
        self.brands = list(db.scalars(select(Brand)).all())
        self._own_brand = next((b for b in self.brands if b.is_own), None)
        # (정규화된 별칭, brand) — 긴 별칭 우선
        self._alias_index: list[tuple[str, Brand]] = []
        for b in self.brands:
            names = set(b.aliases_json or [])
            names.add(b.name)
            for alias in names:
                if alias:
                    self._alias_index.append((_normalize(alias), b))
        self._alias_index.sort(key=lambda x: len(x[0]), reverse=True)
        # 정규화 별칭 → brand 정확매칭 맵(제목 첫 토큰 매칭용 — 부분일치 오탐 방지)
        self._exact_alias: dict[str, Brand] = {a: b for a, b in self._alias_index if a}
        # 공식 카탈로그: base_code → (mapped_category_id, is_accessory)
        self._catalog: dict[str, tuple[int | None, bool]] = {
            cm.base_code: (cm.mapped_category_id, cm.is_accessory)
            for cm in db.scalars(select(CuckooModel)).all()
        }

    def _catalog_lookup(self, title: str) -> tuple[int | None, bool] | None:
        """제목의 모델코드가 공식 카탈로그에 있으면 (category_id, is_accessory) 반환."""
        for m in _CODE_TOKEN_RE.finditer((title or "").upper()):
            info = self._catalog.get(normalize_code(m.group(1)))
            if info is not None:
                return info
        return None

    def is_strong_own(self, brand_raw: str = "", title: str = "", maker_raw: str = "") -> bool:
        """자사 보조 검색('쿠쿠 {카테고리}') 결과 필터용 — 진짜 쿠쿠만 True.

        카탈로그 매칭 또는 brand/maker가 쿠쿠 제조사 별칭과 정확일치할 때만 채택.
        제목 토큰·부분일치(리셀러 '쿠쿠스토어' 등)는 제외 — 보조검색 관련도 노이즈 차단.
        """
        if self._own_brand is None:
            return False
        if self._catalog_lookup(title) is not None:
            return True
        own_aliases = {a for a, b in self._exact_alias.items() if b.is_own}
        return _normalize(brand_raw) in own_aliases or _normalize(maker_raw) in own_aliases

    def _leading_brand(self, title: str) -> Brand | None:
        """제목 앞쪽 토큰이 브랜드 별칭과 '정확히' 일치하면 그 브랜드.

        네이버 제목은 보통 '브랜드 제품명…' 형태라 첫 토큰이 브랜드다.
        시작 토큰 정확일치만 보므로 부분문자열 오탐(예: '보아르'에 '오아')이 없다.
        대괄호/괄호로 시작하는 토큰(예: '[26년형]')은 건너뛴다.
        """
        # 첫 '의미 토큰' 1개만 검사 — 대괄호/괄호 토큰만 건너뛰고, 그 다음 토큰이 브랜드.
        # 2번째 토큰까지 보면 '만토 쿠쿠 …'처럼 제품명 속 단어를 브랜드로 오인하므로 1개로 제한.
        for tok in (title or "").split():
            if tok[:1] in "[(":
                continue
            nt = _normalize(tok)
            if not nt:
                continue
            return self._exact_alias.get(nt)  # 첫 의미토큰이 별칭과 정확일치할 때만
        return None

    def match(
        self,
        brand_raw: str = "",
        title: str = "",
        category_name: str | None = None,
        maker_raw: str = "",
    ) -> MatchResult:
        """판별(균형) — 자사(쿠쿠)는 카탈로그 OR 구조화된 쿠쿠 제조사 식별자로 인정.

        정책:
        - 카탈로그(productlist.xlsx) 매칭 → 자사 0.99(+카테고리 권위).
        - 그 외엔 brand_raw/maker/제목 첫 토큰이 '정확히' 쿠쿠 제조사 별칭(쿠쿠전자·
          쿠쿠홈시스·CUCKOO·쿠쿠)일 때만 자사. 부분일치·제품명 속 '쿠쿠'는 불인정
          → 리셀러 '쿠쿠스토어'·'만토 쿠쿠'·'쿠쿠토이즈' 등 오탐 차단.
        경쟁사는 brand_raw(0.95) > maker(0.93) > 제목 첫 토큰(0.90), 부분일치 허용.
        """
        # 0단계: 공식 카탈로그(productlist.xlsx) 매칭 — 자사+카테고리 권위
        if self._own_brand:
            cat_info = self._catalog_lookup(title)
            if cat_info is not None:
                mapped_cat, is_acc = cat_info
                return MatchResult(
                    self._own_brand.id, True, 0.99, "catalog", mapped_cat, is_acc
                )

        # brand_raw: 자사는 정확일치만(리셀러 substring 차단), 경쟁사는 부분일치 허용.
        nb = _normalize(brand_raw)
        if nb:
            for alias, brand in self._alias_index:
                if alias and ((alias == nb) if brand.is_own else (alias in nb)):
                    return MatchResult(brand.id, bool(brand.is_own), 0.95, "brand_field")

        nm = _normalize(maker_raw)
        if nm:
            for alias, brand in self._alias_index:
                if alias and ((alias == nm) if brand.is_own else (alias in nm)):
                    return MatchResult(brand.id, bool(brand.is_own), 0.93, "maker_field")

        # 제목 첫 토큰 = 브랜드(자사·경쟁사 공통, 정확일치). '만토 쿠쿠'는 첫토큰 만토라 제외.
        lead = self._leading_brand(title)
        if lead is not None:
            return MatchResult(lead.id, bool(lead.is_own), 0.90, "title_brand")

        return MatchResult(None, False, 0.0, "none")
