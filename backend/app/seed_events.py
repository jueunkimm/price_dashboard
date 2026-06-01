"""프로모션 캘린더 시드(F10) — 시즌성/정기 세일 이벤트.

실행:  python -m app.seed_events
변동 추세에서 시즌 노이즈를 분리·해석하기 위한 기준 이벤트(기획서 2.2-G).
멱등: 같은 title+start_date 있으면 건너뜀.
"""
from datetime import date

from sqlalchemy import select

from app.database import Base, SessionLocal, engine
from app.models import MarketEvent

# (title, event_type, start, end, note)
EVENTS = [
    ("신학기·이사철 수요기", "season", date(2026, 2, 15), date(2026, 3, 15), "혼수·신혼·이사 가전 수요 상승"),
    ("가정의 달 프로모션", "sale", date(2026, 5, 1), date(2026, 5, 15), "5월 가전 행사 집중"),
    ("여름 시즌가전 성수기", "season", date(2026, 6, 1), date(2026, 7, 31), "에어컨·제습기·선풍기 수요 급증"),
    ("코리아세일페스타(코세페)", "sale", date(2026, 11, 1), date(2026, 11, 15), "정부 주도 대규모 할인 행사"),
    ("블랙프라이데이/11.11", "sale", date(2026, 11, 11), date(2026, 11, 28), "연중 최대 가격 하락 구간"),
    ("연말 결산 세일", "sale", date(2026, 12, 20), date(2026, 12, 31), "재고 소진·연식 변경 대비"),
]


def seed_events() -> int:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    added = 0
    try:
        for title, etype, start, end, note in EVENTS:
            exists = db.scalar(
                select(MarketEvent).where(
                    MarketEvent.title == title, MarketEvent.start_date == start
                )
            )
            if not exists:
                db.add(
                    MarketEvent(
                        title=title,
                        event_type=etype,
                        start_date=start,
                        end_date=end,
                        note=note,
                    )
                )
                added += 1
        db.commit()
        print(f"[seed_events] 이벤트 {added}개 추가")
        return added
    finally:
        db.close()


if __name__ == "__main__":
    seed_events()
