"""경량 마이그레이션 — create_all로는 추가되지 않는 신규 컬럼을 보강.

대부분의 경우 create_all이 신규 DB의 모든 컬럼을 만들므로 불필요하지만,
기존 DB에 컬럼을 추가할 때 사용한다. PostgreSQL/SQLite 둘 다 지원.

실행:  python -m app.migrate
"""
from sqlalchemy import inspect, text

from app import models  # noqa: F401 — Base.metadata에 모든 테이블 등록
from app.database import Base, engine

# (테이블, 컬럼, 타입+기본값) — 이미 있으면 무시
COLUMNS = [
    ("product", "is_rental", "BOOLEAN NOT NULL DEFAULT 0"),
    ("product", "is_accessory", "BOOLEAN NOT NULL DEFAULT 0"),
    ("product", "model_key", "VARCHAR(120)"),
    ("product", "sub_category", "VARCHAR(60)"),
    ("product", "naver_cat", "VARCHAR(60)"),
    ("product", "image_url", "VARCHAR(500)"),
    ("product", "link", "VARCHAR(500)"),
    ("product", "capacity_value", "DOUBLE PRECISION"),
    ("product", "capacity_unit", "VARCHAR(20)"),
    ("price_snapshot", "is_synthetic", "BOOLEAN NOT NULL DEFAULT 0"),
]


def migrate() -> None:
    Base.metadata.create_all(bind=engine)  # 신규 테이블/컬럼 보장
    insp = inspect(engine)
    existing_tables = set(insp.get_table_names())
    with engine.begin() as conn:
        for table, column, ddl in COLUMNS:
            if table not in existing_tables:
                continue
            cols = {c["name"] for c in insp.get_columns(table)}
            if column in cols:
                continue  # 이미 있음
            conn.execute(text(f'ALTER TABLE "{table}" ADD COLUMN {column} {ddl}'))
            print(f"[migrate] {table}.{column} 추가")
    print("[migrate] 완료")


if __name__ == "__main__":
    migrate()
