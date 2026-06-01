"""알림 규칙 평가 실행(F11) — 인앱 알림 생성.

실행:  python -m collector.evaluate_alerts
(스케줄러/수집 후 호출하면 변동 발생분이 알림으로 쌓임)
"""
from __future__ import annotations

from app.alerts import evaluate
from app.database import SessionLocal


def main() -> dict:
    db = SessionLocal()
    try:
        return evaluate(db)
    finally:
        db.close()


if __name__ == "__main__":
    import json

    print(json.dumps(main(), ensure_ascii=False))
