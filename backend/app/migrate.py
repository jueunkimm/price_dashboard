"""경량 마이그레이션 — create_all로는 추가되지 않는 신규 컬럼을 ALTER로 보강.

실행:  python -m app.migrate
(운영 전환 시 Alembic로 대체 권장. MVP 단계의 멱등 보조 도구)
"""
from sqlalchemy import text

from app.database import Base, engine

# (테이블, 컬럼, 타입+기본값) — 이미 있으면 무시
COLUMNS = [
    ("product", "is_rental", "BOOLEAN NOT NULL DEFAULT FALSE"),
    ("product", "is_accessory", "BOOLEAN NOT NULL DEFAULT FALSE"),
    ("product", "model_key", "VARCHAR(120)"),
    ("product", "capacity_value", "DOUBLE PRECISION"),
    ("product", "capacity_unit", "VARCHAR(20)"),
    ("price_snapshot", "is_synthetic", "BOOLEAN NOT NULL DEFAULT FALSE"),
]


def migrate() -> None:
    Base.metadata.create_all(bind=engine)  # 신규 테이블 보장
    with engine.begin() as conn:
        for table, column, ddl in COLUMNS:
            conn.execute(
                text(f'ALTER TABLE "{table}" ADD COLUMN IF NOT EXISTS {column} {ddl}')
            )
            print(f"[migrate] {table}.{column} 보장 완료")


if __name__ == "__main__":
    migrate()
