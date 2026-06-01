"""수집 스케줄러(F6) — 매주 월·금 정기 수집.

실행:  python -m collector.scheduler
(즉시 1회 수집 후, 매주 월/금 09:00 KST 가격·알림 + 09:30 수요)
주의: 이 프로세스가 켜져 있고 PC가 깨어 있어야 해당 시각에 수집됨.
"""
from apscheduler.schedulers.blocking import BlockingScheduler

from app.alerts import evaluate
from app.database import SessionLocal
from collector.collect import run_collection


def collect_and_alert() -> None:
    """가격 수집 → 변동 알림 평가까지 한 사이클(주 2회: 월·금)."""
    run_collection()
    db = SessionLocal()
    try:
        result = evaluate(db)
        print(f"[scheduler] 알림 평가: {result}")
    finally:
        db.close()


def collect_demand_job() -> None:
    """수요 트렌드(F7) 수집."""
    try:
        from collector.collect_demand import run_demand

        result = run_demand(days=90)
        print(f"[scheduler] 수요 수집: {result}")
    except Exception as e:  # noqa: BLE001 — 데이터랩 실패가 다른 작업을 막지 않도록
        print(f"[scheduler] 수요 수집 건너뜀: {e}")


def collect_macro_job() -> None:
    """환율(F12) 수집 — ECOS."""
    try:
        from collector.collect_macro import run_macro

        result = run_macro(days=120)
        print(f"[scheduler] 환율 수집: {result}")
    except Exception as e:  # noqa: BLE001 — ECOS 실패가 다른 작업을 막지 않도록
        print(f"[scheduler] 환율 수집 건너뜀: {e}")


def collect_cuckoo_job() -> None:
    """쿠쿠 공식 카탈로그 모델 직접 수집 — 완전한 자사 라인업 가격 갱신."""
    try:
        from collector.collect_cuckoo import run_cuckoo_collection

        result = run_cuckoo_collection()
        print(f"[scheduler] 쿠쿠 카탈로그 수집: {result}")
    except Exception as e:  # noqa: BLE001
        print(f"[scheduler] 쿠쿠 카탈로그 수집 건너뜀: {e}")


def main() -> None:
    print("[scheduler] 시작 — 즉시 1회(가격+알림+쿠쿠+수요+환율) 후 매주 월·금 반복")
    collect_and_alert()
    collect_cuckoo_job()
    collect_demand_job()
    collect_macro_job()

    scheduler = BlockingScheduler(timezone="Asia/Seoul")
    # 가격·알림: 매주 월·금 09:00
    scheduler.add_job(
        collect_and_alert, "cron", day_of_week="mon,fri", hour=9, minute=0, id="biweekly_collect"
    )
    # 쿠쿠 카탈로그: 매주 월·금 09:10
    scheduler.add_job(
        collect_cuckoo_job, "cron", day_of_week="mon,fri", hour=9, minute=10, id="biweekly_cuckoo"
    )
    # 수요·환율: 매주 월·금 09:30 (API 호출 절약)
    scheduler.add_job(
        collect_demand_job, "cron", day_of_week="mon,fri", hour=9, minute=30, id="biweekly_demand"
    )
    scheduler.add_job(
        collect_macro_job, "cron", day_of_week="mon,fri", hour=9, minute=35, id="biweekly_macro"
    )
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        print("[scheduler] 종료")


if __name__ == "__main__":
    main()
