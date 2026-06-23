"""DB 모델 — 기획서 6장 스키마 기준.

MVP 핵심: category, brand, product, price_snapshot, collection_log.
(demand_metric / macro_metric / market_event / alert_rule 는 Phase 2~3에서 추가)
"""
from datetime import datetime, date

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Category(Base):
    __tablename__ = "category"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), index=True)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("category.id"), nullable=True)
    level: Mapped[int] = mapped_column(Integer, default=1)  # 1=대분류, 2=소분류
    # 쿠쿠 라인업 보유 카테고리(★) 표식 — 화면 정렬/뱃지용
    has_own_lineup: Mapped[bool] = mapped_column(Boolean, default=False)
    # 네이버쇼핑 검색에 사용할 키워드(소분류명과 다를 수 있음)
    search_keyword: Mapped[str | None] = mapped_column(String(100), nullable=True)

    parent: Mapped["Category | None"] = relationship(remote_side=[id], backref="children")
    products: Mapped[list["Product"]] = relationship(back_populates="category")


class Brand(Base):
    __tablename__ = "brand"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)  # 표준 브랜드명
    is_own: Mapped[bool] = mapped_column(Boolean, default=False)  # 자사(쿠쿠) 여부
    # 별칭 사전: ["쿠쿠","CUCKOO","쿠쿠전자","쿠쿠홈시스"]
    aliases_json: Mapped[list | None] = mapped_column(JSON, nullable=True)

    products: Mapped[list["Product"]] = relationship(back_populates="brand")


class Product(Base):
    __tablename__ = "product"

    id: Mapped[int] = mapped_column(primary_key=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("category.id"), index=True)
    brand_id: Mapped[int | None] = mapped_column(ForeignKey("brand.id"), nullable=True, index=True)
    brand_raw: Mapped[str | None] = mapped_column(String(200), nullable=True)  # 수집 원문 브랜드 표기
    is_own_brand: Mapped[bool] = mapped_column(Boolean, default=False, index=True)  # 쿠쿠 제품 여부(빠른 필터)
    is_rental: Mapped[bool] = mapped_column(Boolean, default=False, index=True)  # 렌탈 상품(월렌탈료) 여부
    is_accessory: Mapped[bool] = mapped_column(Boolean, default=False, index=True)  # 부품/소모품(비교 제외)
    model_key: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)  # 모델 단위 dedup 키
    sub_category: Mapped[str | None] = mapped_column(String(60), nullable=True, index=True)  # 네이버 세부분류(category4) 예: 드럼세탁기
    naver_cat: Mapped[str | None] = mapped_column(String(60), nullable=True, index=True)  # 네이버 상위분류(category3) 예: 세탁/건조기 — 카테고리 정합성 점검용
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)  # 네이버 상품 썸네일 URL(핫링크)
    link: Mapped[str | None] = mapped_column(String(500), nullable=True)  # 네이버 상품 페이지 URL
    capacity_value: Mapped[float | None] = mapped_column(Float, nullable=True)  # 용량 수치(스펙 정규화)
    capacity_unit: Mapped[str | None] = mapped_column(String(20), nullable=True)  # 단위(인용/L/평 등)
    model_name: Mapped[str] = mapped_column(String(300), index=True)
    spec_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # 네이버 상품 식별자(중복 적재 방지용)
    external_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    release_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    category: Mapped["Category"] = relationship(back_populates="products")
    brand: Mapped["Brand | None"] = relationship(back_populates="products")
    snapshots: Mapped[list["PriceSnapshot"]] = relationship(back_populates="product")


class PriceSnapshot(Base):
    __tablename__ = "price_snapshot"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("product.id"), index=True)
    channel: Mapped[str] = mapped_column(String(50), default="naver")  # naver/coupang/danawa...
    list_price: Mapped[int] = mapped_column(Integer)  # 표시가
    effective_price: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 실질가(F8)
    in_stock: Mapped[bool | None] = mapped_column(Boolean, nullable=True)  # 재고(F9)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=False, index=True)  # 합성/데모 데이터 여부
    source: Mapped[str | None] = mapped_column(String(100), nullable=True)  # 쇼핑몰명 등
    collected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    product: Mapped["Product"] = relationship(back_populates="snapshots")


class DemandMetric(Base):
    """수요/트렌드(F7) — 네이버 데이터랩 검색어 트렌드 등."""
    __tablename__ = "demand_metric"

    id: Mapped[int] = mapped_column(primary_key=True)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("category.id"), nullable=True, index=True)
    metric_type: Mapped[str] = mapped_column(String(40), default="search_trend")  # search_trend/rank/click_index
    period: Mapped[date] = mapped_column(Date, index=True)  # 해당 값의 기준일
    value: Mapped[float] = mapped_column(Float)  # 데이터랩 상대지수(0~100)
    source: Mapped[str | None] = mapped_column(String(50), nullable=True)
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class MarketEvent(Base):
    """이벤트/프로모션 캘린더(F10)."""
    __tablename__ = "market_event"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(120))
    event_type: Mapped[str] = mapped_column(String(30))  # sale/launch/season
    category_id: Mapped[int | None] = mapped_column(ForeignKey("category.id"), nullable=True)
    start_date: Mapped[date] = mapped_column(Date, index=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)


class CuckooModel(Base):
    """쿠쿠 공식 모델 카탈로그(방법 B) — 권위있는 자사 모델/제품군/카테고리 사전."""
    __tablename__ = "cuckoo_model"

    id: Mapped[int] = mapped_column(primary_key=True)
    model_code: Mapped[str] = mapped_column(String(120), index=True)  # 원문 모델명
    base_code: Mapped[str] = mapped_column(String(120), index=True)  # 정규화(색상/리비전 제거)
    product_group: Mapped[str] = mapped_column(String(60))  # 쿠쿠 제품군
    mapped_category_id: Mapped[int | None] = mapped_column(
        ForeignKey("category.id"), nullable=True
    )  # 대시보드 카테고리(매핑)
    is_accessory: Mapped[bool] = mapped_column(Boolean, default=False)  # 별매품 여부


class DanawaSpec(Base):
    """다나와 구조화 사양 캐시 — 모델코드로 다나와를 조회해 정확한 제품유형/용량을 확보.
    네이버 제목엔 없는 사양(로봇청소기 흡입력 등)을 채우는 권위 소스. 모델코드 단위 캐시."""
    __tablename__ = "danawa_spec"

    id: Mapped[int] = mapped_column(primary_key=True)
    model_key: Mapped[str] = mapped_column(String(120), unique=True, index=True)  # 정규화 모델코드
    status: Mapped[str] = mapped_column(String(20), default="pending")  # matched/notfound/error
    danawa_type: Mapped[str | None] = mapped_column(String(60), nullable=True)  # spec 첫 토큰(제품유형)
    matched_name: Mapped[str | None] = mapped_column(String(300), nullable=True)
    raw_spec: Mapped[str | None] = mapped_column(String(1000), nullable=True)  # spec_list 원문
    capacity_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    capacity_unit: Mapped[str | None] = mapped_column(String(20), nullable=True)
    capacity_band: Mapped[str | None] = mapped_column(String(40), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class MacroMetric(Base):
    """거시지표(F12) — 환율/금리/물가 등."""
    __tablename__ = "macro_metric"

    id: Mapped[int] = mapped_column(primary_key=True)
    metric_type: Mapped[str] = mapped_column(String(40), index=True)  # usd_krw / cpi / base_rate
    period: Mapped[date] = mapped_column(Date, index=True)
    value: Mapped[float] = mapped_column(Float)
    source: Mapped[str | None] = mapped_column(String(50), nullable=True)
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AlertRule(Base):
    """변동 알림 규칙(F11)."""
    __tablename__ = "alert_rule"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    scope: Mapped[str] = mapped_column(String(40), default="all")  # all / own / category:<id>
    threshold_pct: Mapped[float] = mapped_column(Float, default=10.0)
    direction: Mapped[str] = mapped_column(String(10), default="both")  # up / down / both
    channel: Mapped[str] = mapped_column(String(20), default="inapp")  # inapp / email / slack
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Alert(Base):
    """생성된 알림(F11) — 규칙 평가 결과. 외부 발송은 권한/설정 필요(스캐폴딩)."""
    __tablename__ = "alert"

    id: Mapped[int] = mapped_column(primary_key=True)
    rule_id: Mapped[int | None] = mapped_column(ForeignKey("alert_rule.id"), nullable=True)
    product_id: Mapped[int | None] = mapped_column(ForeignKey("product.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(300))
    change_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_own_brand: Mapped[bool] = mapped_column(Boolean, default=False)
    period: Mapped[date] = mapped_column(Date, index=True)  # 알림 기준일(중복 방지)
    dispatched: Mapped[bool] = mapped_column(Boolean, default=False)  # 외부발송 여부
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CollectionLog(Base):
    """수집 로그(F6) — 실행 단위 결과 기록."""
    __tablename__ = "collection_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="running")  # running/success/error
    categories_done: Mapped[int] = mapped_column(Integer, default=0)
    products_collected: Mapped[int] = mapped_column(Integer, default=0)
    snapshots_inserted: Mapped[int] = mapped_column(Integer, default=0)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
