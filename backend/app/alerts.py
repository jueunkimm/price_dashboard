"""변동 알림(F11) — 규칙 평가 + 인앱 알림 생성.

설계 원칙(안전):
- 인앱 알림(Alert 레코드) 생성까지가 자동.
- 이메일/슬랙 등 **외부 발송은 사용자 자격증명·설정과 명시적 동의가 필요**하므로
  여기서는 디스패처 인터페이스만 두고 실제 전송은 하지 않는다(dispatched=False).
"""
from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import aggregation
from app.models import Alert, AlertRule


def _rule_matches(rule: AlertRule, row: dict) -> bool:
    if rule.scope == "own" and not row["is_own_brand"]:
        return False
    if rule.scope.startswith("category:"):
        # category 이름 스코프는 MVP 범위 밖 — all/own만 평가
        return False
    change = row["change_pct"]
    if change is None or abs(change) < rule.threshold_pct:
        return False
    if rule.direction == "up" and change <= 0:
        return False
    if rule.direction == "down" and change >= 0:
        return False
    return True


def evaluate(db: Session, on_date: date | None = None) -> dict:
    """활성 규칙을 오늘 변동 랭킹에 적용해 알림 생성(중복일 방지)."""
    on_date = on_date or date.today()
    rules = list(db.scalars(select(AlertRule).where(AlertRule.is_active.is_(True))).all())
    if not rules:
        return {"created": 0, "rules": 0}

    ranking = aggregation.movement_ranking(db, is_own_only=False, limit=10000)
    created = 0
    for rule in rules:
        for row in ranking:
            if not _rule_matches(rule, row):
                continue
            # 같은 (rule, product, 날짜) 알림이 이미 있으면 건너뜀
            exists = db.scalar(
                select(Alert).where(
                    Alert.rule_id == rule.id,
                    Alert.product_id == row["product_id"],
                    Alert.period == on_date,
                )
            )
            if exists:
                continue
            arrow = "▲" if row["change_pct"] > 0 else "▼"
            db.add(
                Alert(
                    rule_id=rule.id,
                    product_id=row["product_id"],
                    title=f"[{row['category_name']}] {arrow}{abs(row['change_pct']):.1f}% · {row['model_name'][:60]}",
                    change_pct=row["change_pct"],
                    is_own_brand=row["is_own_brand"],
                    period=on_date,
                    dispatched=False,  # 외부 발송은 별도 설정 필요
                )
            )
            created += 1
    db.commit()
    return {"created": created, "rules": len(rules)}


def dispatch_external(alert: Alert) -> bool:
    """외부 채널(이메일/슬랙) 발송 자리표시자.

    실제 발송은 SMTP/Webhook 자격증명과 사용자 동의가 필요하므로 미구현(False 반환).
    """
    return False
