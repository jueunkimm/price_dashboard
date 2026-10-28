"""다나와 카테고리 코드 매핑 빌더 — 우리 카테고리(66개) ↔ 다나와 cate 코드.

방식(재설계안 §3 Track A):
  1) 각 카테고리의 search_keyword로 다나와 통합검색
  2) 검색결과에 포함된 카테고리 링크(/list/?cate=NNNN)의 최빈값을 후보로 채택
  3) 후보 cate의 목록 페이지를 열어 다나와 분류명·상품수로 검증
  4) backend/app/danawa_cate_map.json 저장 (검토 후 커밋 — 런타임 수집기는 이 파일만 읽음)

실행:  python -m collector.danawa_cate_map            # 전체 생성
       python -m collector.danawa_cate_map 세탁기      # 단일 카테고리 재매핑
"""
from __future__ import annotations

import io
import json
import re
import sys
from collections import Counter
from pathlib import Path

from sqlalchemy import select

from app.database import SessionLocal
from app.models import Category
from collector.danawa_v2 import _fetch, category_products

MAP_PATH = Path(__file__).resolve().parent.parent / "app" / "danawa_cate_map.json"


def discover_cate(keyword: str) -> list[tuple[str, int]]:
    """검색결과에서 카테고리 링크 최빈 cate 코드 상위 후보 반환."""
    page = _fetch(f"https://search.danawa.com/?query={keyword}")
    cates = re.findall(r"prod\.danawa\.com/list/\?[^\"]*?cate=(\d+)", page)
    return Counter(cates).most_common(3)


def verify_cate(cate: str) -> dict:
    """후보 cate 목록 1페이지로 검증 — 다나와 분류명·상품수."""
    rows = category_products(cate, page=1)
    names = rows[0]["cate_names"] if rows else []
    return {"count": len(rows), "danawa_names": names}


def build(target: str | None = None) -> dict:
    db = SessionLocal()
    try:
        cats = list(db.scalars(select(Category).where(Category.level == 2)).all())
    finally:
        db.close()
    existing: dict = {}
    if MAP_PATH.exists():
        existing = json.loads(MAP_PATH.read_text(encoding="utf-8"))

    out = dict(existing)
    for c in cats:
        if target and c.name != target:
            continue
        kw = c.search_keyword or c.name
        try:
            candidates = discover_cate(kw)
            if not candidates:
                out[c.name] = {"cate": None, "note": "검색결과에 카테고리 링크 없음", "keyword": kw}
                print(f"  ✗ {c.name}: 후보 없음")
                continue
            cate, votes = candidates[0]
            v = verify_cate(cate)
            out[c.name] = {
                "cate": cate,
                "keyword": kw,
                "votes": votes,
                "alt": [cc for cc, _ in candidates[1:]],
                **v,
            }
            print(f"  ✓ {c.name}: cate={cate} ({votes}표) → {'>'.join(v['danawa_names'])} [{v['count']}개]")
        except Exception as e:  # noqa: BLE001 — 개별 실패가 전체를 막지 않게
            out[c.name] = {"cate": None, "note": f"오류: {e}", "keyword": kw}
            print(f"  ✗ {c.name}: {e}")

    MAP_PATH.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    ok = sum(1 for v in out.values() if v.get("cate"))
    print(f"[danawa_cate_map] 저장: {MAP_PATH.name} — 매핑 {ok}/{len(out)}")
    return out


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    build(sys.argv[1] if len(sys.argv) > 1 else None)
