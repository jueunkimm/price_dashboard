# 가전 가격트래킹 대시보드

전체 가전 카테고리 가격·변동률을 트래킹하고, 그 안에서 **쿠쿠(CUCKOO) 자사 제품**을 분리·비교하는 대시보드. (Phase 1 / MVP)

- 기획서: [`가전_가격트래킹_대시보드_기획서.md`](가전_가격트래킹_대시보드_기획서.md)
- 작업 리스트: [`작업리스트.md`](작업리스트.md)

## 스택
- **프론트**: React + Vite + TypeScript + Tailwind + Recharts (`frontend/`)
- **백엔드**: FastAPI + SQLAlchemy (`backend/app/`)
- **수집기**: Python + 네이버쇼핑 OpenAPI + APScheduler (`backend/collector/`)
- **DB**: PostgreSQL (Docker)

## 디렉터리
```
price_dashboard/
├── docker-compose.yml         # postgres
├── .env                       # 시크릿(네이버 키 등) — git 제외
├── backend/
│   ├── requirements.txt
│   ├── app/                   # FastAPI + 모델 + 집계
│   │   ├── main.py            # 앱 진입점
│   │   ├── models.py          # DB 스키마(기획서 6장)
│   │   ├── aggregation.py     # 변동률/집계/쿠쿠 포지셔닝
│   │   ├── seed.py            # 카테고리·쿠쿠 브랜드 시드
│   │   └── api/routes.py      # REST API
│   └── collector/             # 수집기
│       ├── naver_client.py    # 네이버쇼핑 API
│       ├── brand_matcher.py   # 쿠쿠 별칭 매칭
│       ├── collect.py         # 수집 잡
│       └── scheduler.py       # 1일 2회 스케줄
└── frontend/                  # 대시보드 UI
```

## 실행 순서

### 0) 사전 준비
- Docker Desktop 설치·실행
- `.env`에 네이버 `NAVER_CLIENT_ID` / `NAVER_CLIENT_SECRET` 설정(완료)

### 1) DB 기동
```powershell
docker compose up -d
```

### 2) 백엔드 설치 & 시드
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m app.seed          # 카테고리 + 쿠쿠 브랜드 시드
```

### 3) 가격 수집(최초 1회)
```powershell
python -m collector.collect       # 네이버에서 카테고리별 가격 수집
# 정기 수집: python -m collector.scheduler  (매주 월·금 09:00 가격·알림 / 09:30 수요)
#   ※ 이 프로세스가 켜져 있고 PC가 켜져 있어야 해당 시각에 수집됨
```

### 3-1) 보강 스크립트(선택)
```powershell
python -m app.migrate                       # 신규 컬럼 보강(is_rental 등)
python -m collector.reclassify              # 쿠쿠 매칭/렌탈 플래그 재계산(재수집 불필요)
python -m app.seed_events                    # 프로모션·시즌 이벤트 시드(F10)
python -m collector.collect_demand --days 90 # 데이터랩 수요 트렌드(검색+쇼핑인사이트) — 데이터랩 권한 필요

# Phase 2~3
python -m app.seed_alerts                    # 기본 알림 규칙(F11)
python -m collector.evaluate_alerts          # 변동 알림 평가·생성(F11, 인앱) — 실수집 2일+ 필요
python -m collector.collect_macro --days 120 # 환율(F12) — ECOS_API_KEY 필요
python -m app.report                         # 주간 요약 리포트(F13) 마크다운 출력

# 쿠쿠 공식 카탈로그(방법 B) — productlist.xlsx 필요
python -m app.cuckoo_catalog                  # 공식 모델 1231개 적재(제품군→카테고리 매핑·별매품)
python -m collector.collect_cuckoo            # 카탈로그 모델코드로 네이버 직접 수집(완전한 쿠쿠 라인업)

# QA 1차 조치(데이터 정제·경쟁사)
python -m app.seed_brands                    # 경쟁 브랜드 별칭 시드(B-2)
pytest tests                                 # 회귀 테스트(매처/정제 로직)
python qa_check.py                           # 자동 QA(pytest + DB 무결성) — JSON 출력
```

> **자동 QA 훅**: `.claude/settings.json`에 Stop 훅이 설정되어 매 턴 종료 시 `qa_check.py`가
> 자동 실행됩니다(pytest + 데이터 무결성 점검 → 결과를 systemMessage로 고지, 비차단).
> 새 settings 파일은 세션 중 생성 시 `/hooks` 열기 또는 재시작 후 활성화됩니다.

> **데이터 정제**: `reclassify`/`collect`가 부품(`is_accessory`)·렌탈(`is_rental`)·모델키
> (`model_key`)·용량(`capacity_*`)을 자동 산출. 집계는 부품·렌탈 제외 + 모델 단위 dedup.
> **신뢰성**: `/api/data-quality`로 실측일수·합성여부 확인. 변동률은 실수집 2일+ 누적 시 실데이터화.

> **F12 실데이터(환율)**: 한국은행 ECOS 인증키 필요. https://ecos.bok.or.kr/api 에서 발급 후
> `.env`에 `ECOS_API_KEY=...` 추가 → `collector/ecos_client.py` 사용.
> **F11 외부 발송**: 인앱 알림까지 자동. 이메일/슬랙 발송은 SMTP/Webhook 자격증명과
> 명시적 동의가 필요해 스캐폴딩만 두었습니다(`app/alerts.py::dispatch_external`).

> **F7 실데이터 활성화**: 네이버 데이터랩(검색어트렌드)은 별도 권한이 필요합니다.
> https://developers.naver.com → 내 애플리케이션 → **API 설정 → "데이터랩(검색어트렌드)" 추가** 후
> `python -m collector.collect_demand` 실행 시 합성 데이터가 실데이터로 교체됩니다.

### 4) 백엔드 API
```powershell
uvicorn app.main:app --reload     # http://localhost:8000/docs
```

### 5) 프론트
```powershell
cd frontend
npm install
npm run dev                       # http://localhost:5173
```

## 참고
- 변동률(시계열)은 수집이 **며칠 누적**되어야 채워집니다(첫날은 변동 0/None).
- 공식 API 우선·rate limit 준수 등 법적 유의사항은 기획서 5.2 참조.
- 운영 전환 시 스키마는 Alembic 마이그레이션으로 관리 권장(현재는 기동 시 create_all).
