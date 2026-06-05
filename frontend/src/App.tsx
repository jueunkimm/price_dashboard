import { useEffect, useMemo, useState } from "react";
import {
  api,
  type CategoryOverview,
  type Kpi,
  type ProductFilters,
  type RankingRow,
} from "./api";
import KpiBar from "./components/KpiBar";
import CategoryGrid from "./components/CategoryGrid";
import MovementTable from "./components/MovementTable";
import TrendChart from "./components/TrendChart";
import PositioningPanel from "./components/PositioningPanel";
import CollectionStatus from "./components/CollectionStatus";
import EventsPanel from "./components/EventsPanel";
import DemandPanel from "./components/DemandPanel";
import AlertsPanel from "./components/AlertsPanel";
import ReportPanel from "./components/ReportPanel";
import MacroChip from "./components/MacroChip";
import DataQualityBanner from "./components/DataQualityBanner";
import BrandComparePanel from "./components/BrandComparePanel";
import SearchBox from "./components/SearchBox";
import FilterBar from "./components/FilterBar";
import ProductResults from "./components/ProductResults";
import Scorecard from "./components/Scorecard";

const TODAY = "2026-06-01";

type Tab = "market" | "own" | "alerts";
const TABS: { key: Tab; label: string }[] = [
  { key: "market", label: "시장 현황" },
  { key: "own", label: "쿠쿠 분석" },
  { key: "alerts", label: "알림·이벤트" },
];

export default function App() {
  const [ownOnly, setOwnOnly] = useState(false);
  const [tab, setTab] = useState<Tab>("market");
  const [kpi, setKpi] = useState<Kpi | null>(null);
  const [cats, setCats] = useState<CategoryOverview[]>([]);
  const [ranking, setRanking] = useState<RankingRow[]>([]);
  const [selectedProduct, setSelectedProduct] = useState<number | null>(null);
  const [filters, setFilters] = useState<ProductFilters>({ exclude_rental: true });
  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setErr(null);
    setLoading(true);
    Promise.all([api.kpi(ownOnly), api.categories(ownOnly), api.ranking(ownOnly, 200)])
      .then(([k, c, r]) => {
        setKpi(k);
        setCats(c);
        setRanking(r);
      })
      .catch((e) => setErr(String(e)))
      .finally(() => setLoading(false));
  }, [ownOnly]);

  const patchFilters = (patch: Partial<ProductFilters>) =>
    setFilters((f) => ({ ...f, ...patch }));

  // 선택된 카테고리(사이드바/그리드 공유)
  const selectedCat = useMemo(
    () => cats.find((c) => c.category_id === filters.category_id) ?? null,
    [cats, filters.category_id]
  );

  const pickProduct = (id: number) => {
    setSelectedProduct(id);
    setTab("market");
  };

  const Legend = (
    <div className="flex items-center gap-3 text-[11px] text-slate-400">
      <span>
        <span className="text-up">▲ 빨강</span> = 가격 상승
      </span>
      <span>
        <span className="text-down">▼ 파랑</span> = 가격 하락
      </span>
      <span className="text-slate-300">· 변동률은 직전 수집 대비</span>
    </div>
  );

  const KpiArea =
    loading && !kpi ? (
      <div className="grid grid-cols-2 xl:grid-cols-4 gap-3">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="rounded-xl bg-white p-4 border border-slate-100 animate-pulse">
            <div className="h-3 w-16 bg-slate-100 rounded mb-2" />
            <div className="h-5 w-24 bg-slate-100 rounded" />
          </div>
        ))}
      </div>
    ) : (
      <KpiBar kpi={kpi} ownOnly={ownOnly} />
    );

  return (
    <div className="min-h-screen">
      <header className="bg-white border-b border-slate-200 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between gap-3 flex-wrap">
          <div className="min-w-0">
            <h1 className="text-base sm:text-lg font-bold truncate">
              가전 가격트래킹 대시보드
              <span className="ml-2 text-[11px] font-normal text-slate-400">{TODAY} 기준</span>
            </h1>
            <CollectionStatus />
          </div>
          <div className="flex items-center gap-2 shrink-0 order-3 sm:order-2 w-full sm:w-auto">
            <SearchBox ownOnly={ownOnly} onSelect={pickProduct} />
          </div>
          <div className="flex items-center gap-2 shrink-0 order-2 sm:order-3">
            <MacroChip />
            <button
              onClick={() => setOwnOnly((v) => !v)}
              className={`px-3 sm:px-4 py-2 rounded-lg text-sm font-medium transition ${
                ownOnly ? "bg-own text-white" : "bg-slate-100 text-slate-600"
              }`}
            >
              {ownOnly ? "★ 쿠쿠만 보기" : "전체 보기"}
            </button>
          </div>
        </div>
        <div className="max-w-7xl mx-auto px-4 flex gap-1">
          {TABS.map((t) => (
            <button
              key={t.key}
              onClick={() => setTab(t.key)}
              className={`px-3 py-2 text-sm font-medium border-b-2 -mb-px transition ${
                tab === t.key
                  ? "border-own text-own"
                  : "border-transparent text-slate-400 hover:text-slate-600"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-5 space-y-6">
        {err && (
          <div className="rounded-lg bg-red-50 text-red-600 text-sm p-3 border border-red-100">
            데이터를 불러오지 못했습니다: {err}
            <div className="text-xs text-red-400 mt-1">
              데이터(/data/*.json)가 아직 생성되지 않았을 수 있습니다. 수집·export 후 다시 시도하세요.
            </div>
          </div>
        )}

        <DataQualityBanner />

        {tab === "market" && (
          <div className="space-y-6">
            <FilterBar cats={cats} filters={filters} onChange={patchFilters} />

            <div className="space-y-6">
              {KpiArea}
              {Legend}

              {selectedCat ? (
                // ── 카테고리 상세(사이드바 선택) ──
                <>
                  <div className="flex items-center justify-between">
                    <h2 className="text-sm font-semibold text-slate-700">
                      {selectedCat.has_own_lineup ? "★ " : ""}
                      {selectedCat.category_name}
                      {filters.capacity_band && (
                        <span className="text-own ml-1">· {filters.capacity_band}</span>
                      )}
                    </h2>
                    <button
                      onClick={() =>
                        patchFilters({
                          category_id: undefined,
                          capacity_band: undefined,
                          brand_id: undefined,
                        })
                      }
                      className="text-xs text-own hover:underline"
                    >
                      전체 카테고리로 ✕
                    </button>
                  </div>

                  <BrandComparePanel
                    categoryId={selectedCat.category_id}
                    categoryName={selectedCat.category_name}
                    filters={filters}
                  />

                  <div className="grid lg:grid-cols-5 gap-6">
                    <section className="lg:col-span-3 min-w-0">
                      <h2 className="text-sm font-semibold text-slate-500 mb-2">제품 목록</h2>
                      <ProductResults
                        filters={filters}
                        ownOnly={ownOnly}
                        onSelect={setSelectedProduct}
                      />
                    </section>
                    <section className="lg:col-span-2 min-w-0 space-y-4">
                      <div>
                        <h2 className="text-sm font-semibold text-slate-500 mb-2">가격 추세</h2>
                        <TrendChart productId={selectedProduct} />
                      </div>
                      {selectedProduct && (
                        <div>
                          <h2 className="text-sm font-semibold text-slate-500 mb-2">동급 경쟁 스코어카드</h2>
                          <Scorecard productId={selectedProduct} />
                        </div>
                      )}
                      <DemandPanel
                        categoryId={selectedCat.category_id}
                        categoryName={selectedCat.category_name}
                      />
                    </section>
                  </div>
                </>
              ) : (
                // ── 전체 개요(카테고리 미선택) ──
                <>
                  <ReportPanel />

                  <section>
                    <h2 className="text-sm font-semibold text-slate-500 mb-2">
                      카테고리 현황
                      <span className="ml-2 text-xs font-normal text-slate-400">
                        카드 또는 왼쪽 필터로 카테고리 선택 → 상세
                      </span>
                    </h2>
                    {loading && cats.length === 0 ? (
                      <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-3">
                        {Array.from({ length: 8 }).map((_, i) => (
                          <div
                            key={i}
                            className="rounded-xl bg-white p-4 border border-slate-100 animate-pulse h-24"
                          />
                        ))}
                      </div>
                    ) : (
                      <CategoryGrid
                        cats={cats}
                        selectedId={filters.category_id ?? null}
                        onSelect={(c) => patchFilters({ category_id: c?.category_id })}
                      />
                    )}
                  </section>

                  <div className="grid lg:grid-cols-2 gap-6">
                    <section>
                      <h2 className="text-sm font-semibold text-slate-500 mb-2">변동 랭킹</h2>
                      <MovementTable rows={ranking} onSelect={setSelectedProduct} />
                    </section>
                    <section>
                      <h2 className="text-sm font-semibold text-slate-500 mb-2">가격 추세</h2>
                      <TrendChart productId={selectedProduct} />
                    </section>
                  </div>
                </>
              )}
            </div>
          </div>
        )}

        {tab === "own" && (
          <>
            {KpiArea}
            <div className="text-xs text-slate-400">
              쿠쿠 가격 포지셔닝 — 부품·렌탈 제외, 모델 단위 집계. 동급(용량) 비교는 토글로 전환.
            </div>
            <PositioningPanel />
          </>
        )}

        {tab === "alerts" && (
          <div className="grid lg:grid-cols-2 gap-6">
            <section>
              <h2 className="text-sm font-semibold text-slate-500 mb-2">변동 알림</h2>
              <AlertsPanel ownOnly={ownOnly} />
            </section>
            <section>
              <h2 className="text-sm font-semibold text-slate-500 mb-2">시장 이벤트</h2>
              <EventsPanel today={TODAY} />
            </section>
          </div>
        )}
      </main>
    </div>
  );
}
