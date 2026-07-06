import { useEffect, useState } from "react";
import { api, type CategoryOverview, type FilterOptions, type ProductFilters } from "../../api";

// 디자인 핸드오프 상세 필터 카드 — 전체현황·카테고리 상세뷰 양쪽에서 공용.
// 카테고리 선택 시에도 유지되어 용량·브랜드·판매몰·가격대·구분으로 정밀 분석 가능.
const SEL =
  "border border-[#e0e0e6] rounded-lg px-2.5 py-2.5 text-[13px] bg-white focus:outline-none focus:ring-1 focus:ring-own/40";
const LBL = "flex flex-col gap-1.5";
const LBLT = "text-[11px] text-[#8e8e99] font-semibold";

export default function FilterCard({
  cats,
  filters,
  onFilters,
  onPickCategory,
}: {
  cats: CategoryOverview[];
  filters: ProductFilters;
  onFilters: (patch: Partial<ProductFilters>) => void;
  onPickCategory: (categoryId: number) => void;
}) {
  const [opts, setOpts] = useState<FilterOptions | null>(null);

  // 카테고리 선택 시 해당 카테고리의 용량·브랜드·판매몰 옵션으로 좁힘
  useEffect(() => {
    api.filterOptions(filters.category_id).then(setOpts).catch(() => setOpts(null));
  }, [filters.category_id]);

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

  return (
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
  );
}
