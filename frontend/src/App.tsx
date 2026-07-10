import { useEffect, useMemo, useState } from "react";
import {
  api,
  type CategoryOverview,
  type Kpi,
  type Macro,
  type ProductFilters,
  type RankingRow,
} from "./api";
import { won } from "./format";
import { C } from "./components/dash/util";
import FilterCard from "./components/dash/FilterCard";
import MarketTab from "./components/dash/MarketTab";
import CuckooTab from "./components/dash/CuckooTab";
import AlertsTab from "./components/dash/AlertsTab";
import CategoryDetail from "./components/dash/CategoryDetail";
import ProductResults from "./components/ProductResults";

// 이벤트 타임라인 '오늘' 마커 — 실제 현재 날짜(로컬) 사용
const TODAY = (() => {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
})();

type Tab = "market" | "cuckoo" | "alerts";
const TABS: { key: Tab; label: string }[] = [
  { key: "market", label: "시장 현황" },
  { key: "cuckoo", label: "쿠쿠 분석" },
  { key: "alerts", label: "알림·이벤트" },
];

// 헤더 환율 셀 — 직전 영업일 대비 상승 ▲(빨강)/하락 ▼(파랑)/보합 ─
function FxCell({ label, latest, prev }: { label: string; latest: number | null; prev: number | null }) {
  const dir = latest != null && prev != null ? Math.sign(latest - prev) : 0;
  return (
    <div className="flex flex-col items-end">
      <span className="text-[10px] text-[#9a9aa2] font-semibold tracking-wide">{label}</span>
      <span className="text-[13px] font-bold tabular-nums">
        {latest != null ? latest.toFixed(1) : "—"}
        {latest != null && (
          <span className={`text-[11px] ml-0.5 ${dir > 0 ? "text-up" : dir < 0 ? "text-down" : "text-[#bcbcc4]"}`}>
            {dir > 0 ? "▲" : dir < 0 ? "▼" : "─"}
          </span>
        )}
      </span>
    </div>
  );
}

// 디자인 핸드오프 KPI 스트립 (시장·쿠쿠 탭)
function KpiStrip({ kpi }: { kpi: Kpi | null }) {
  if (!kpi) {
    return (
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3.5">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="bg-white border border-[#e9e9ee] rounded-[14px] px-[18px] py-4 animate-pulse h-[88px]" />
        ))}
      </div>
    );
  }
  const fmtPct = (n: number | null | undefined) => (n == null ? "-" : (n > 0 ? "+" : "") + n.toFixed(2) + "%");
  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3.5">
      <div className="bg-white border border-[#e9e9ee] rounded-[14px] px-[18px] py-4">
        <div className="text-xs text-[#8e8e99] font-semibold">트래킹 제품 수</div>
        <div className="text-[26px] font-extrabold tracking-[-0.02em] mt-1.5 tabular-nums">
          {kpi.product_count.toLocaleString("ko-KR")}
        </div>
      </div>
      <div className="bg-white border border-[#e9e9ee] rounded-[14px] px-[18px] py-4">
        <div className="text-xs text-[#8e8e99] font-semibold">평균 변동률</div>
        <div className="text-[26px] font-extrabold tracking-[-0.02em] mt-1.5 tabular-nums">
          {kpi.avg_change_pct == null ? "-" : kpi.avg_change_pct.toFixed(2) + "%"}
        </div>
      </div>
      <div className="bg-white border border-[#e9e9ee] rounded-[14px] px-[18px] py-4">
        <div className="text-xs text-[#8e8e99] font-semibold">급변 제품 수</div>
        <div className="text-[26px] font-extrabold tracking-[-0.02em] mt-1.5 tabular-nums" style={{ color: C.up }}>
          {kpi.anomaly_count.toLocaleString("ko-KR")}
        </div>
      </div>
      <div className="bg-white border border-[#e9e9ee] rounded-[14px] px-[18px] py-4">
        <div className="text-xs text-[#8e8e99] font-semibold">최대 등락</div>
        <div className="flex flex-col gap-[3px] mt-2">
          <span className="text-[15px] font-bold tabular-nums" style={{ color: C.up }}>
            ▲ {fmtPct(kpi.top_up?.change_pct)}
            {kpi.top_up && <span className="text-[#9a9aa2] font-medium text-xs"> · {won(kpi.top_up.current_price)}</span>}
          </span>
          <span className="text-[15px] font-bold tabular-nums" style={{ color: C.down }}>
            ▼ {fmtPct(kpi.top_down?.change_pct)}
            {kpi.top_down && <span className="text-[#9a9aa2] font-medium text-xs"> · {won(kpi.top_down.current_price)}</span>}
          </span>
        </div>
      </div>
    </div>
  );
}

export default function App() {
  const [ownOnly, setOwnOnly] = useState(false);
  const [tab, setTab] = useState<Tab>("market");
  const [q, setQ] = useState("");
  const [kpi, setKpi] = useState<Kpi | null>(null);
  const [cats, setCats] = useState<CategoryOverview[]>([]);
  const [ranking, setRanking] = useState<RankingRow[]>([]);
  const [macro, setMacro] = useState<Macro | null>(null);
  const [collected, setCollected] = useState<string>("");
  const [filters, setFilters] = useState<ProductFilters>({ pricing: "onetime" });
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    setErr(null);
    Promise.all([api.kpi(ownOnly), api.categories(ownOnly), api.ranking(ownOnly, 200)])
      .then(([k, c, r]) => {
        setKpi(k);
        setCats(c);
        setRanking(r);
      })
      .catch((e) => setErr(String(e)));
  }, [ownOnly]);

  useEffect(() => {
    api.macro().then(setMacro).catch(() => setMacro(null));
    api
      .collectionLogs(1)
      .then((logs) => {
        const f = logs[0]?.finished_at;
        if (f) {
          const d = new Date(f);
          if (!isNaN(d.getTime())) setCollected(d.toLocaleString("ko-KR"));
        }
      })
      .catch(() => setCollected(""));
  }, []);

  const patchFilters = (patch: Partial<ProductFilters>) => setFilters((f) => ({ ...f, ...patch }));

  const selectedCat = useMemo(
    () => cats.find((c) => c.category_id === filters.category_id) ?? null,
    [cats, filters.category_id]
  );

  const pickCategory = (categoryId: number) => {
    patchFilters({ category_id: categoryId });
    setTab("market");
  };
  const clearCategory = () =>
    patchFilters({ category_id: undefined, capacity_band: undefined, brand_id: undefined, sub_category: undefined });

  const totalCount = kpi?.product_count ?? 0;
  const showKpi = tab !== "alerts" && !selectedCat;

  return (
    <div className="min-h-screen">
      {/* 헤더 */}
      <header className="sticky top-0 z-20 bg-white/90 backdrop-blur-[8px] border-b border-[#e6e6ec]">
        <div className="max-w-[1240px] mx-auto px-6 pt-3.5">
          <div className="flex items-start gap-5">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2.5">
                <div className="w-[26px] h-[26px] rounded-[7px] bg-ink text-white flex items-center justify-center text-[13px] font-extrabold">
                  가
                </div>
                <h1 className="text-[18px] font-extrabold tracking-[-0.02em] truncate">가전 가격트래킹 대시보드</h1>
              </div>
              <div className="flex items-center gap-2 mt-1.5 text-xs text-[#8e8e99] flex-wrap">
                <span className="w-[7px] h-[7px] rounded-full bg-[#3fa56a] inline-block" />
                <span>최근 수집 {collected || "—"}</span>
                <span className="text-[#d3d3da]">·</span>
                <span>
                  {cats.length}개 카테고리 · {totalCount.toLocaleString("ko-KR")}건
                </span>
              </div>
            </div>
            <div className="flex items-center gap-2.5 pt-0.5 shrink-0">
              <div className="hidden sm:flex items-center gap-1.5 bg-[#f1f1f4] border border-[#e6e6ec] rounded-[9px] px-3 py-2">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#9a9aa2" strokeWidth="2.2">
                  <circle cx="11" cy="11" r="7" />
                  <path d="m21 21-4.3-4.3" />
                </svg>
                <input
                  value={q}
                  onChange={(e) => setQ(e.target.value)}
                  placeholder="제품·카테고리 검색"
                  className="bg-transparent outline-none w-[150px] text-[13px]"
                />
              </div>
              {/* 환율 pill — USD·CNY(매매기준율) + 직전 영업일 대비 방향 + 기준일 */}
              <div className="hidden md:flex flex-col items-end border border-[#e6e6ec] rounded-[9px] px-3 py-1.5 bg-white">
                <div className="flex items-center gap-3">
                  <FxCell label="USD/KRW" latest={macro?.latest ?? null} prev={macro?.prev ?? null} />
                  <FxCell label="CNY/KRW" latest={macro?.cny?.latest ?? null} prev={macro?.cny?.prev ?? null} />
                </div>
                {macro?.latest_date && (
                  <span className="text-[9px] text-[#bcbcc4] mt-0.5">{macro.latest_date} 기준</span>
                )}
              </div>
              <button
                onClick={() => setOwnOnly((v) => !v)}
                className={`text-[13px] font-semibold px-4 py-2.5 rounded-[9px] ${
                  ownOnly ? "bg-own text-white" : "bg-ink text-white"
                }`}
              >
                {ownOnly ? "★ 쿠쿠만" : "전체 보기"}
              </button>
            </div>
          </div>
          <nav className="flex gap-1 mt-3.5">
            {TABS.map((t) => (
              <button
                key={t.key}
                onClick={() => setTab(t.key)}
                className={`px-4 pt-[11px] pb-[13px] text-[14px] font-semibold border-b-2 -mb-px transition ${
                  tab === t.key ? "border-own text-ink" : "border-transparent text-[#9a9aa2] hover:text-[#6b6b73]"
                }`}
              >
                {t.label}
              </button>
            ))}
          </nav>
        </div>
      </header>

      <main className="max-w-[1240px] mx-auto px-6 pt-[22px] pb-[72px] space-y-[22px]">
        {err && (
          <div className="rounded-lg bg-red-50 text-red-600 text-sm p-3 border border-red-100">
            데이터를 불러오지 못했습니다: {err}
            <div className="text-xs text-red-400 mt-1">
              데이터(/data/*.json)가 아직 생성되지 않았을 수 있습니다. 수집·export 후 다시 시도하세요.
            </div>
          </div>
        )}

        {showKpi && <KpiStrip kpi={kpi} />}

        {tab === "market" && (
          <>
            {/* 상세 필터는 전체현황·카테고리 상세 양쪽에서 항상 노출(정밀 분석 유지) */}
            <FilterCard cats={cats} filters={filters} onFilters={patchFilters} onPickCategory={pickCategory} />
            {selectedCat ? (
              <CategoryDetail
                cat={selectedCat}
                filters={filters}
                ownOnly={ownOnly}
                onPatchFilters={patchFilters}
                onClear={clearCategory}
              />
            ) : (
              <>
                {/* 헤더 검색어는 랭킹(변동 있는 상위만)이 아니라 전체 제품(products.json)을 검색 */}
                {q.trim() && (
                  <section className="space-y-2">
                    <div className="flex items-center gap-2 flex-wrap">
                      <h2 className="text-[15px] font-bold text-ink">"{q.trim()}" 검색 결과</h2>
                      <span className="text-xs text-[#9a9aa2]">
                        전체 제품 대상 · 행 클릭 시 해당 카테고리 상세로
                      </span>
                      <button onClick={() => setQ("")} className="text-xs text-own hover:underline">
                        검색 지우기 ✕
                      </button>
                    </div>
                    <ProductResults
                      filters={{ ...filters, q: q.trim() }}
                      ownOnly={ownOnly}
                      onSelect={(_, categoryId) => {
                        if (categoryId) pickCategory(categoryId);
                      }}
                    />
                  </section>
                )}
                <MarketTab cats={cats} ranking={ranking} q={q} onPickCategory={pickCategory} />
              </>
            )}
          </>
        )}

        {tab === "cuckoo" && <CuckooTab onPick={pickCategory} />}

        {tab === "alerts" && <AlertsTab ownOnly={ownOnly} today={TODAY} />}
      </main>
    </div>
  );
}
