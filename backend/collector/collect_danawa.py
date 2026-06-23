"""다나와 구조화 사양 수집 — 모델코드로 다나와를 조회해 정확한 제품유형/용량을 확보.

배경: 네이버 검색 제목엔 사양이 일부만 담겨(로봇청소기 흡입력 등 누락) 용량 필터가
빈약하다. 다나와는 제품별 구조화 사양('spec_list')을 제공하므로, 우리 제품의 모델코드로
다나와를 검색해 정확한 사양을 가져와 캐시(DanawaSpec)한다. reclassify가 이를 우선 사용.

설계:
  - 모델코드(model_key) 단위 캐시. 이미 조회한 코드는 건너뜀(증분). DB 캐시로 누적.
  - 1회 실행당 MAX_PER_RUN개만 신규 조회(시간 제한) → 여러 수집에 걸쳐 전체 커버.
  - 정확매칭: 검색 결과 중 '액세서리/부품'이 아니고 이름에 모델코드가 든 첫 상품 채택.
  - 용량: 깨끗한 spec_list 문자열에 extract_spec(카테고리)를 적용(제목보다 정확).
  - 예의상 요청 간 지연. 실패는 status에 기록하고 계속(비차단).

실행:  python -m collector.collect_danawa
"""
from __future__ import annotations

import re
import time

import httpx
from sqlalchemy import select

from app.cuckoo_catalog import normalize_code
from app.database import Base, SessionLocal, engine
from app.models import Category, DanawaSpec, Product
from app.spec import extract_spec

MAX_PER_RUN = 400          # 1회 실행당 신규 조회 상한(증분)
SLEEP = 0.4                # 요청 간 지연(예의)
_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
_ACC_HINT = ("액세서리", "호환", "정품 ", "비정품", "소모품", "필터", "브러쉬", "세트", "거치대", "전용")
_PROD_SPLIT = re.compile(r'<li[^>]*class="[^"]*prod_item')
_NAME_RE = re.compile(r'class="prod_name"[^>]*>\s*<a[^>]*>(.*?)</a>', re.S)
_SPEC_RE = re.compile(r'class="spec_list"[^>]*>(.*?)</div>', re.S)


def _clean(html: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html)).strip()


def _search(client: httpx.Client, code: str) -> dict | None:
    """모델코드로 검색해 (제품유형, spec_list, 매칭이름) 반환. 없으면 None."""
    r = client.get(
        "https://search.danawa.com/dsearch.php",
        params={"query": code}, timeout=15, follow_redirects=True,
    )
    if r.status_code != 200:
        return None
    ncode = normalize_code(code).replace("-", "").upper()
    for blk in _PROD_SPLIT.split(r.text)[1:]:
        nm = _NAME_RE.search(blk)
        sm = _SPEC_RE.search(blk)
        if not nm or not sm:
            continue
        name = _clean(nm.group(1))
        spec = _clean(sm.group(1))
        if any(h in name or h in spec[:12] for h in _ACC_HINT):
            continue  # 부품/액세서리 제외
        if ncode not in name.replace("-", "").replace(" ", "").upper():
            continue  # 모델코드 정확 매칭만
        dtype = spec.split("/")[0].strip() if spec else None
        return {"type": dtype, "spec": spec[:1000], "name": name[:300]}
    return None


def run_danawa_collection() -> dict:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        cat_name = {c.id: c.name for c in db.scalars(select(Category)).all()}
        done = set(db.scalars(select(DanawaSpec.model_key)).all())
        # 본품·비렌탈 제품의 고유 모델코드(카테고리 1개 동반)
        targets: dict[str, int] = {}
        for p in db.scalars(
            select(Product).where(
                Product.model_key.is_not(None),
                Product.is_accessory.is_(False),
                Product.is_rental.is_(False),
            )
        ).all():
            if p.model_key and p.model_key not in done and p.model_key not in targets:
                targets[p.model_key] = p.category_id

        todo = list(targets.items())[:MAX_PER_RUN]
        matched = notfound = 0
        with httpx.Client(headers={"User-Agent": _UA, "Accept-Language": "ko-KR"}) as client:
            for code, cid in todo:
                rec = DanawaSpec(model_key=code)
                try:
                    info = _search(client, code)
                    if info:
                        cap_v, cap_u, band = extract_spec(cat_name.get(cid), info["spec"])
                        rec.status = "matched"
                        rec.danawa_type = (info["type"] or "")[:60]
                        rec.matched_name = info["name"]
                        rec.raw_spec = info["spec"]
                        rec.capacity_value, rec.capacity_unit, rec.capacity_band = cap_v, cap_u, band
                        matched += 1
                    else:
                        rec.status = "notfound"
                        notfound += 1
                except Exception as e:  # noqa: BLE001
                    rec.status = "error"
                    rec.raw_spec = str(e)[:200]
                db.add(rec)
                if (matched + notfound) % 50 == 0:
                    db.commit()
                    print(f"[danawa] 진행 {matched + notfound}/{len(todo)} (매칭 {matched})")
                time.sleep(SLEEP)
        db.commit()
        result = {"new_queries": len(todo), "matched": matched, "notfound": notfound,
                  "total_cached": len(done) + len(todo)}
        print(f"[danawa] 완료: {result}")
        return result
    finally:
        db.close()


if __name__ == "__main__":
    import json

    print(json.dumps(run_danawa_collection(), ensure_ascii=False, indent=2))
