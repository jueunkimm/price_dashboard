"""쿠쿠 공식 모델 카탈로그(방법 B) — 제품군→카테고리 매핑 + 적재.

엑셀(productlist.xlsx, 제품군/모델명)을 읽어 cuckoo_model 테이블에 적재한다.
제품군은 쿠쿠 분류 → 대시보드 31개 카테고리로 매핑(없으면 None).
"""
from __future__ import annotations

import re
from pathlib import Path

from sqlalchemy import select

from app.database import Base, SessionLocal, engine
from app.models import Category, CuckooModel

XLSX_PATH = Path(__file__).resolve().parents[2] / "productlist.xlsx"

# 쿠쿠 제품군 → 대시보드 카테고리명 (없으면 None = 매핑 안 함)
GROUP_TO_CATEGORY: dict[str, str | None] = {
    "IH전기압력밥솥": "전기밥솥",
    "전기압력밥솥": "전기밥솥",
    "전기보온밥솥": "전기밥솥",
    "멀티쿠커": "멀티쿠커",
    "인덕션레인지": "인덕션·전기레인지",
    "가스레인지": "인덕션·전기레인지",
    "정수기": "정수기",
    "필터형정수기": "정수기",
    "POU정수기": "정수기",
    "세정.연수기": "정수기",
    "공기청정기": "공기청정기",
    "비데": "비데",
    "전자레인지": "전자레인지·오븐",
    "진공청소기": "무선청소기",
    "청소기": "무선청소기",
    "로봇청소기": "로봇청소기",
    "식기세척기": "식기세척기",
    "써큘레이터": "선풍기·서큘레이터",
    "실링팬": "선풍기·서큘레이터",
    "벽걸이 에어컨": "에어컨",
    "창문형에어컨": "에어컨",
    "블렌더": "믹서·블렌더",
    "두유제조기": "믹서·블렌더",
    "에어프라이어": "에어프라이어",
    "제습기": "제습기",
    "가습기": "가습기",
    "김치냉장고": "김치냉장고",
    "냉장고": "냉장고",
    "냉동고": "냉장고",
    "세탁기": "세탁기",
    "의류건조기": "건조기",
    "안마기기": "안마의자·안마기",
    "카본히터": "전기히터·온풍기",
    "히터기": "전기히터·온풍기",
    "커피머신": "커피머신",
    "헤어드라이어": "헤어드라이어·스타일러",
    "헤어아이론": "헤어드라이어·스타일러",
    "스팀다리미": "스팀다리미",
    # 신규 카테고리 매핑 — 카탈로그가 올바른 카테고리로 이동시켜 ★(자사 라인업) 정확화
    "음식물처리기": "음식물처리기",
    "전기주전자": "전기포트",
    "토스터기": "토스터",
    "제빵기": "제빵기",
    "프라이팬": "전기프라이팬",
    "제빙기": "제빙기",
    "전기그릴": "전기그릴",
    "전동칫솔": "전동칫솔",
    "카본매트": "온수매트",
    "워터클렌져": "구강세정기",
    "구강관리기": "구강세정기",
    "LED마스크": "피부미용기",
    "스킨케어디바이스": "피부미용기",
    # 매핑 없음(대시보드 카테고리 부재): 별매품/펫*/생선구이기/레인지후드/식기건조기
}

ACCESSORY_GROUPS = {"별매품", "펫별매품"}


def normalize_code(code: str) -> str:
    """모델코드 정규화 — 색상/리비전 접미 제거. 'CRP-AHF1020FD(R)' → 'CRP-AHF1020FD'."""
    return re.split(r"[ (]", str(code).upper().strip())[0]


def seed_catalog(path: Path | None = None) -> dict:
    import openpyxl

    Base.metadata.create_all(bind=engine)
    path = path or XLSX_PATH
    wb = openpyxl.load_workbook(str(path), read_only=True, data_only=True)
    ws = wb["Sheet1"]

    db = SessionLocal()
    try:
        # 이미 적재돼 있으면 초기화(재적재)
        if db.scalar(select(CuckooModel).limit(1)):
            db.query(CuckooModel).delete()
            db.commit()

        cat_id = {c.name: c.id for c in db.scalars(select(Category).where(Category.level == 2)).all()}
        seen: set[str] = set()
        added = 0
        mapped = 0
        accessory = 0
        for row in ws.iter_rows(min_row=3, values_only=True):
            group, model = row[1], row[2]
            if not group or not model:
                continue
            base = normalize_code(model)
            if base in seen:
                continue
            seen.add(base)
            is_acc = group in ACCESSORY_GROUPS
            cat_name = GROUP_TO_CATEGORY.get(group)
            mcid = cat_id.get(cat_name) if cat_name else None
            db.add(
                CuckooModel(
                    model_code=str(model).strip(),
                    base_code=base,
                    product_group=str(group).strip(),
                    mapped_category_id=mcid,
                    is_accessory=is_acc,
                )
            )
            added += 1
            mapped += 1 if mcid else 0
            accessory += 1 if is_acc else 0
        db.commit()
        return {"models": added, "mapped_to_category": mapped, "accessories": accessory}
    finally:
        db.close()


if __name__ == "__main__":
    import json

    print(json.dumps(seed_catalog(), ensure_ascii=False, indent=2))
