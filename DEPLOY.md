# 평생 무료 배포 가이드 (GitHub Actions + GitHub Pages)

이 대시보드는 **백엔드 없는 정적 웹앱**으로 동작합니다.
GitHub Actions가 매일 **09:00 / 15:00(KST)** 자동으로 데이터를 수집해 정적 JSON을 만들고,
GitHub Pages가 그 결과를 **평생 무료**로 호스팅합니다. (PC를 켜둘 필요 없음)

```
[GitHub Actions cron 09/15시]
   네이버·데이터랩·ECOS 수집 → 집계 → /data/*.json 생성 → 프론트 빌드
                                              │
                                       [GitHub Pages] ←─ URL로 어디서나 접속
   가격 히스토리(SQLite)는 Actions 캐시에 누적(변동률 계산용)
```

---

## 한 번만 하면 되는 설정

### 1. GitHub 레포 만들기 + 코드 올리기
GitHub 계정으로 **새 레포(예: `price-dashboard`)** 를 만든 뒤, 이 폴더에서:

```powershell
cd C:\Users\22025064\Documents\price_dashboard
git init
git add .
git commit -m "init: 가전 가격트래킹 대시보드"
git branch -M main
git remote add origin https://github.com/<내아이디>/price-dashboard.git
git push -u origin main
```

> `.env`(API 키)는 `.gitignore`로 **올라가지 않습니다.** 키는 아래 Secrets로 등록합니다.

### 2. API 키를 레포 Secrets에 등록
레포 → **Settings → Secrets and variables → Actions → New repository secret** 에서 3개 추가:

| 이름 | 값 |
|------|-----|
| `NAVER_CLIENT_ID` | 네이버 Client ID |
| `NAVER_CLIENT_SECRET` | 네이버 Client Secret |
| `ECOS_API_KEY` | 한국은행 ECOS 키 |

### 3. GitHub Pages 켜기
레포 → **Settings → Pages → Build and deployment → Source: `GitHub Actions`** 선택.

### 4. 첫 실행(수동)
레포 → **Actions → "collect-and-deploy" → Run workflow** 클릭.
- 첫 실행은 시드+전체 수집이라 **5~8분** 걸립니다.
- 완료되면 **Settings → Pages**에 배포 URL이 표시됩니다 (예: `https://<내아이디>.github.io/price-dashboard/`).

이후엔 **매일 09:00 / 15:00(KST)** 자동 실행됩니다. (끝.)

---

## 알아둘 점
- **변동률**: 자동 수집이 **2회 이상 누적**되면 변동률·추세·랭킹·알림이 채워집니다(첫날은 비어 있음 — 정상).
- **cron 시간**: GitHub 무료 cron은 정시보다 **수 분~수십 분 지연**될 수 있습니다(무료 특성).
- **비용**: 공개(public) 레포면 Actions 무제한 무료. 데이터(가전 가격)는 민감정보가 아니라 공개 레포 권장.
  비공개 레포도 월 2,000분 무료라 충분합니다(1회 ~8분 × 2회 × 30일 ≈ 480분).
- **히스토리 보존**: SQLite DB는 Actions 캐시에 저장됩니다. 2회/일 cron이라 항상 갱신되어 유지됩니다.
- 🔒 **보안**: 채팅에 노출된 키가 걱정되면 네이버/ECOS에서 재발급 후 Secrets만 갱신하세요.

## 로컬에서 미리 보기(선택)
백엔드 없이 정적 데이터로 바로 볼 수 있습니다:
```powershell
cd backend; python -m app.export_static      # /data/*.json 생성(현재 DB 기준)
cd ..\frontend; npm run dev                    # http://localhost:5173
```
