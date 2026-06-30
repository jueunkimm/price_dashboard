import { useEffect, useState } from "react";
import {
  api,
  type CategoryOverview,
  type FilterOptions,
  type ProductFilters,
  type RankingRow,
  type WeeklyReport,
} from "../../api";
import { C } from "./util";
import RankCompare from "./RankCompare";
import CategoryTable from "./CategoryTable";

// 디자인 핸드오프 — 시장 현황 탭: 상세필터 + 주간요약 + 랭킹/비교 + 카테고리표
const SEL =
  "border border-[#e0e0e6] rounded-lg px-2.5 py-2.5 text-[13px] bg-white focus:outline-none focus:ring-1 focus:ring-own/40";
const LBL = "flex flex-col gap-1.5";
const LBLT = "text-[11px] text-[#8e8e99] font-semibold";

export default function MarketTab({
  cats,
  ranking,
  q,
  filters,
  onFilters,
  onPickCategory,
}: {
  cats: CategoryOverview[];
  ranking: RankingRow[];
  q: string;
  filters: ProductFilters;
  onFilters: (patch: Partial<ProductFilters>) => void;
  onPickCategory: (categoryId: number) => void;
}) {
  const [opts, setOpts] = useState<FilterOptions | null>(null);
  const [weekly, setWeekly] = useState<WeeklyReport | null>(null);

  useEffect(() => {
    api.filterOptions(filters.category_id).then(setOpts).catch(() => setOpts(null));
  }, [filters.category_id]);
  useEffect(() => {
    api.report().then(setWeekly).catch(() => setWeekly(null));
  }, []);

  const seg = filters.pricing ?? "onetime";
  const segBtn = (val: "onetime" | "rental" | "all", label: string) => (
    <button
      onClick={() => onFilters({ pricing: val })}
      className={`flex-1 py-2 rounded-[7px] text-[13px] font-semibold text-center ${
        seg === val ? "bg-white text-ink shadow-[0_1px_2px_rgba(0,0,0,0.08)]" : "text-[#8e8e99]"
      }`}
    >
      {label}
    </button>
  );

  const weeklyCells: { label: string; val: string; color: string }[] = weekly
    ? [
        { label: "카테고리", val: String(weekly.category_count), color: C.ink },
        {
          label: "평균 변동",
          val: (weekly.avg_category_change_pct ?? 0).toFixed(2) + "%",
          color: C.ink,
        },
        { label: "급변", val: String(weekly.total_anomalies), color: C.up },
        {
          label: "쿠쿠 포지셔닝",
          val:
            weekly.own_avg_positioning_pct == null
              ? "-"
              : (weekly.own_avg_positioning_pct > 0 ? "+" : "") +
                weekly.own_avg_positioning_pct.toFixed(2) +
                "%",
          color: (weekly.own_avg_positioning_pct ?? 0) < 0 ? C.down : C.up,
        },
        { label: "USD/KRW", val: weekly.usd_krw != null ? weekly.usd_krw.toFixed(1) : "-", color: C.ink },
        { label: "오늘 알림", val: String(weekly.alerts_today), color: C.ink },
      ]
    : [];

  return (
    <div className="space-y-[18px]">
      {/* 상세 필터 */}
      <div className="bg-white border border-[#e9e9ee] rounded-[14px] px-[18px] py-4">
        <div className="flex items-center gap-2 mb-3.5">
          <span className="text-sm font-bold">상세 필터</span>
          <span className="text-xs text-[#9a9aa2]">카테고리 · 용량 · 브랜드 · 판매몰 · 가격대</span>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-[repeat(5,1fr)_1.3fr] gap-2.5 items-end">
          <label className={LBL}>
            <span className={LBLT}>카테고리</span>
            <select
              className={SEL}
              value={filters.category_id ?? ""}
              onChange={(e) => {
                const v = e.target.value;
                if (v) onPickCategory(Number(v));
                else onFilters({ category_id: undefined });
              }}
            >
              <option value="">전체 카테고리</option>
              {[...cats]
                .sort((a, b) => a.category_name.localeCompare(b.category_name, "ko"))
                .map((c) => (
                  <option key={c.category_id} value={c.category_id}>
                    {c.category_name}
                  </option>
                ))}
            </select>
          </label>
          <label className={LBL}>
            <span className={LBLT}>용량·규격</span>
            <select
              className={SEL}
              value={filters.capacity_band ?? ""}
              onChange={(e) => onFilters({ capacity_band: e.target.value || undefined })}
            >
              <option value="">전체 용량</option>
              {(opts?.capacity_bands ?? []).map((b) => (
                <option key={b} value={b}>
                  {b}
                </option>
              ))}
            </select>
          </label>
          <label className={LBL}>
            <span className={LBLT}>브랜드</span>
            <select
              className={SEL}
              value={filters.brand_id ?? ""}
              onChange={(e) => onFilters({ brand_id: e.target.value ? Number(e.target.value) : undefined })}
            >
              <option value="">전체 브랜드</option>
              {(opts?.brands ?? []).map((b) => (
                <option key={b.id} value={b.id}>
                  {b.is_own ? "★ " : ""}
                  {b.name}
                </option>
              ))}
            </select>
          </label>
          <label className={LBL}>
            <span className={LBLT}>판매몰</span>
            <select
              className={SEL}
              value={filters.mall ?? ""}
              onChange={(e) => onFilters({ mall: e.target.value || undefined })}
            >
              <option value="">전체 몰</option>
              {(opts?.malls ?? []).map((m) => (
                <option key={m.name} value={m.name}>
                  {m.name} ({m.count})
                </option>
              ))}
            </select>
          </label>
          <label className={LBL}>
            <span className={LBLT}>가격대 (원)</span>
            <div className="flex items-center gap-1.5">
              <input
                type="number"
                placeholder={opts ? String(opts.price_min) : "0"}
                value={filters.min_price ?? ""}
                onChange={(e) => onFilters({ min_price: e.target.value ? Number(e.target.value) : undefined })}
                className="border border-[#e0e0e6] rounded-lg px-2 py-2.5 text-[13px] w-full focus:outline-none focus:ring-1 focus:ring-own/40"
              />
              <span className="text-[#bcbcc4]">~</span>
              <input
                type="number"
                placeholder={opts ? String(opts.price_max) : ""}
                value={filters.max_price ?? ""}
                onChange={(e) => onFilters({ max_price: e.target.value ? Number(e.target.value) : undefined })}
                className="border border-[#e0e0e6] rounded-lg px-2 py-2.5 text-[13px] w-full focus:outline-none focus:ring-1 focus:ring-own/40"
              />
            </div>
          </label>
          <div className={LBL}>
            <span className={LBLT}>구분</span>
            <div className="flex gap-1 bg-[#f1f1f4] rounded-[9px] p-[3px]">
              {segBtn("onetime", "일시불")}
              {segBtn("rental", "렌탈")}
              {segBtn("all", "전체")}
            </div>
          </div>
        </div>
      </div>

      {/* 주간 요약 */}
      {weeklyCells.length > 0 && (
        <div className="flex items-stretch bg-white border border-[#e9e9ee] rounded-[14px] overflow-hidden">
          {weeklyCells.map((w, i) => (
            <div key={w.label} className={`flex-1 px-4 py-3.5 ${i < weeklyCells.length - 1 ? "border-r border-[#f0f0f3]" : ""}`}>
              <div className="text-[11px] text-[#8e8e99] font-semibold">{w.label}</div>
              <div className="text-[19px] font-extrabold tracking-[-0.02em] mt-1.5 tabular-nums" style={{ color: w.color }}>
                {w.val}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* 랭킹 + 비교 */}
      <RankCompare rows={ranking} q={q} />

      {/* 카테고리별 시장 현황 */}
      <CategoryTable cats={cats} q={q} onPick={onPickCategory} />
    </div>
  );
}
