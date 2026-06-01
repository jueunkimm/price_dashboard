"""기본 알림 규칙 시드(F11).

실행:  python -m app.seed_alerts
"""
from sqlalchemy import select

from app.database import Base, SessionLocal, engine
from app.models import AlertRule

RULES = [
    {"name": "전체 급변 10%↑", "scope": "all", "threshold_pct": 10.0, "direction": "both", "channel": "inapp"},
    {"name": "쿠쿠 변동 8%↑", "scope": "own", "threshold_pct": 8.0, "direction": "both", "channel": "inapp"},
]


def seed_alerts() -> int:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    added = 0
    try:
        for r in RULES:
            if not db.scalar(select(AlertRule).where(AlertRule.name == r["name"])):
                db.add(AlertRule(**r))
                added += 1
        db.commit()
        print(f"[seed_alerts] 규칙 {added}개 추가")
        return added
    finally:
        db.close()


if __name__ == "__main__":
    seed_alerts()
