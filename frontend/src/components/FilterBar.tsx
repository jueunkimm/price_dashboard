import { useEffect, useState } from "react";
import { api, type CategoryOverview, type FilterOptions, type ProductFilters } from "../api";

// 상단 접이식 상세 필터 바 (기본 접힘). 접힌 상태에선 적용된 필터를 칩으로 요약.
export default function FilterBar({
  cats,
  filters,
  onChange,
}: {
  cats: CategoryOverview[];
  filters: ProductFilters;
  onChange: (patch: Partial<ProductFilters>) => void;
}) {
  const [opts, setOpts] = useState<FilterOptions | null>(null);
  const [open, setOpen] = useState(false); // 초기 접힘

  useEffect(() => {
    api.filterOptions(filters.category_id).then(setOpts).catch(() => setOpts(null));
  }, [filters.category_id]);

  const catName = cats.find((c) => c.category_id === filters.category_id)?.category_name;
  const brandName = opts?.brands.find((b) => b.id === filters.brand_id)?.name;

  const chips: string[] = [];
  if (catName) chips.push(catName);
  if (filters.capacity_band) chips.push(filters.capacity_band);
  if (brandName) chips.push(brandName);
  if (filters.mall) chips.push(filters.mall);
  if (filters.min_price != null || filters.max_price != null)
    chips.push(`${filters.min_price?.toLocaleString() ?? "0"}~${filters.max_price?.toLocaleString() ?? "∞"}원`);

  const reset = () =>
    onChange({
      category_id: undefined,
      brand_id: undefined,
      capacity_band: undefined,
      mall: undefined,
      min_price: undefined,
      max_price: undefined,
    });

  return (
    <div className="rounded-xl bg-white border border-slate-100 shadow-sm">
      {/* 헤더(토글) */}
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between gap-3 px-4 py-2.5"
      >
        <span className="flex items-center gap-2 min-w-0">
          <span className="text-sm font-semibold text-slate-600 shrink-0">🔎 상세 필터</span>
          {chips.length > 0 && (
            <span className="flex items-center gap-1 min-w-0 overflow-hidden">
              {chips.map((c, i) => (
                <span
                  key={i}
                  className="shrink-0 text-[11px] bg-own/10 text-own px-1.5 py-0.5 rounded truncate"
                >
                  {c}
                </span>
              ))}
            </span>
          )}
          {chips.length === 0 && (
            <span className="text-xs text-slate-400">카테고리·용량·브랜드·판매몰·가격대</span>
          )}
        </span>
        <span className="text-xs text-slate-400 shrink-0">{open ? "접기 ▴" : "펼치기 ▾"}</span>
      </button>

      {/* 본문(펼침) */}
      {open && (
        <div className="border-t border-slate-100 px-4 py-3">
          <div className="grid grid-cols-2 sm:grid-cols-3 xl:grid-cols-6 gap-3">
            <label className="block">
              <span className="text-xs text-slate-500">카테고리</span>
              <select
                value={filters.category_id ?? ""}
                onChange={(e) =>
                  onChange({
                    category_id: e.target.value ? Number(e.target.value) : undefined,
                    capacity_band: undefined,
                    brand_id: undefined,
                    mall: undefined,
                  })
                }
                className="w-full mt-1 text-sm border border-slate-200 rounded-lg px-2 py-1.5"
              >
                <option value="">전체 카테고리</option>
                {cats.map((c) => (
                  <option key={c.category_id} value={c.category_id}>
                    {c.has_own_lineup ? "★ " : ""}
                    {c.category_name}
                  </option>
                ))}
              </select>
            </label>

            <label className="block">
              <span className="text-xs text-slate-500">용량·규격</span>
              <select
                value={filters.capacity_band ?? ""}
                onChange={(e) => onChange({ capacity_band: e.target.value || undefined })}
                disabled={!opts?.capacity_bands.length}
                className="w-full mt-1 text-sm border border-slate-200 rounded-lg px-2 py-1.5 disabled:bg-slate-50 disabled:text-slate-300"
              >
                <option value="">전체 용량</option>
                {opts?.capacity_bands.map((b) => (
                  <option key={b} value={b}>
                    {b}
                  </option>
                ))}
              </select>
            </label>

            <label className="block">
              <span className="text-xs text-slate-500">브랜드</span>
              <select
                value={filters.brand_id ?? ""}
                onChange={(e) => onChange({ brand_id: e.target.value ? Number(e.target.value) : undefined })}
                className="w-full mt-1 text-sm border border-slate-200 rounded-lg px-2 py-1.5"
              >
                <option value="">전체 브랜드</option>
                {opts?.brands.map((b) => (
                  <option key={b.id} value={b.id}>
                    {b.is_own ? "★ " : ""}
                    {b.name}
                  </option>
                ))}
              </select>
            </label>

            <label className="block">
              <span className="text-xs text-slate-500">판매몰(채널)</span>
              <select
                value={filters.mall ?? ""}
                onChange={(e) => onChange({ mall: e.target.value || undefined })}
                className="w-full mt-1 text-sm border border-slate-200 rounded-lg px-2 py-1.5"
              >
                <option value="">전체 몰</option>
                {opts?.malls.map((m) => (
                  <option key={m.name} value={m.name}>
                    {m.name} ({m.count})
                  </option>
                ))}
              </select>
            </label>

            <div>
              <span className="text-xs text-slate-500">가격대 (원)</span>
              <div className="flex items-center gap-1 mt-1">
                <input
                  type="number"
                  value={filters.min_price ?? ""}
                  onChange={(e) =>
                    onChange({ min_price: e.target.value ? Number(e.target.value) : undefined })
                  }
                  placeholder={opts ? String(opts.price_min) : "최소"}
                  className="w-full text-xs border border-slate-200 rounded-lg px-2 py-1.5"
                />
                <span className="text-slate-300">~</span>
                <input
                  type="number"
                  value={filters.max_price ?? ""}
                  onChange={(e) =>
                    onChange({ max_price: e.target.value ? Number(e.target.value) : undefined })
                  }
                  placeholder={opts ? String(opts.price_max) : "최대"}
                  className="w-full text-xs border border-slate-200 rounded-lg px-2 py-1.5"
                />
              </div>
            </div>

            <div className="flex flex-col justify-end gap-1.5 pb-0.5">
              <label className="flex items-center gap-2 text-sm text-slate-600">
                <input
                  type="checkbox"
                  checked={filters.exclude_rental !== false}
                  onChange={(e) => onChange({ exclude_rental: e.target.checked })}
                />
                렌탈 제외
              </label>
              {chips.length > 0 && (
                <button onClick={reset} className="text-xs text-own hover:underline text-left">
                  필터 초기화
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
