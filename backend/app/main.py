"""FastAPI 진입점.

실행:  uvicorn app.main:app --reload  (backend 디렉터리에서)
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.database import Base, engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 개발 편의: 기동 시 테이블 보장 (운영 전환 시 Alembic 권장)
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="가전 가격트래킹 대시보드 API", version="0.1.0", lifespan=lifespan)

# 프론트(Vite 기본 5173) CORS 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/")
def root():
    return {"service": "price-dashboard", "docs": "/docs"}
