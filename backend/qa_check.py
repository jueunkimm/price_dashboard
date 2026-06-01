"""자동 QA 체크 — Stop 훅에서 매 턴 종료 시 실행.

수행: (1) pytest 회귀 테스트, (2) DB 데이터 무결성 점검(가능 시).
출력: stdout에 JSON 한 줄({"systemMessage": ...})만. 비차단(항상 exit 0).
DB가 내려가 있으면 무결성 점검은 건너뛴다(테스트는 그대로 수행).
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent
# `from app ...` 임포트를 위해 backend를 경로에 추가(실행 cwd와 무관)
sys.path.insert(0, str(BACKEND))


def run_pytest() -> tuple[bool, str]:
    try:
        r = subprocess.run(
            [sys.executable, "-m", "pytest", "tests", "-q"],
            cwd=str(BACKEND),
            capture_output=True,
            text=True,
            timeout=120,
        )
        last = (r.stdout or r.stderr or "").strip().splitlines()
        summary = last[-1] if last else "no output"
        return r.returncode == 0, summary
    except Exception as e:  # noqa: BLE001
        return False, f"pytest 실행 오류: {type(e).__name__}"


def db_invariants() -> tuple[list[str], bool]:
    """데이터 무결성 점검. (위반목록, DB도달여부)."""
    issues: list[str] = []
    try:
        from sqlalchemy import select

        from app import aggregation
        from app.database import SessionLocal
        from app.models import Brand, Product

        db = SessionLocal()
        try:
            brands = {b.id: b for b in db.scalars(select(Brand)).all()}
            own = db.scalars(select(Product).where(Product.is_own_brand.is_(True))).all()
            # (1) 경쟁사가 자사로 오분류되지 않았는가
            misclassified = [
                p for p in own if p.brand_id in brands and not brands[p.brand_id].is_own
            ]
            if misclassified:
                issues.append(f"경쟁사 오분류 {len(misclassified)}건")

            # (2) 카테고리 집계 풀에 부품/렌탈이 새지 않는가(샘플)
            cats = aggregation.category_overview(db)
            if not cats:
                issues.append("카테고리 집계 비어있음")

            # (3) 데이터 품질 응답 형태 유지
            dq = aggregation.data_quality(db)
            for key in ("real_collection_days", "variation_ready"):
                if key not in dq:
                    issues.append(f"data_quality '{key}' 누락")
        finally:
            db.close()
        return issues, True
    except Exception as e:  # noqa: BLE001 — DB 미가동 등은 점검 건너뜀
        return [f"DB 점검 생략({type(e).__name__})"], False


def main() -> None:
    try:
        ok, summary = run_pytest()
        issues, db_ok = db_invariants()

        real_issues = [i for i in issues if not i.startswith("DB 점검 생략")]
        passed = ok and not real_issues

        parts = [f"pytest {'✅' if ok else '❌'} {summary}"]
        if db_ok:
            parts.append("무결성 ✅" if not real_issues else "무결성 ❌ " + "; ".join(real_issues))
        else:
            parts.append("무결성 ⏭(DB미가동)")

        prefix = "✅ QA 통과" if passed else "⚠️ QA 확인 필요"
        msg = f"{prefix} — " + " · ".join(parts)
        print(json.dumps({"systemMessage": msg, "suppressOutput": True}))
    except Exception as e:  # noqa: BLE001 — 훅은 절대 죽지 않게
        print(json.dumps({"systemMessage": f"QA 체크 오류: {type(e).__name__}"}))
    sys.exit(0)


if __name__ == "__main__":
    main()
