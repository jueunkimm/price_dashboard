import { useEffect, useState } from "react";
import { api, type BrandRow, type ProductFilters } from "../api";
import { won, pct, changeColor } from "../format";
import { downloadCsv, csvBtnClass } from "../csv";

// 카테고리 내 브랜드별 비교(B-2) — 자사 vs 경쟁사 가격/변동 (제품 목록과 동일 필터)
export default function BrandComparePanel({
  categoryId,
  categoryName,
  filters,
}: {
  categoryId: number;
  categoryName: string;
  filters: ProductFilters;
}) {
  const [rows, setRows] = useState<BrandRow[]>([]);

  useEffect(() => {
    api.brandComparison(categoryId, filters).then(setRows).catch(() => setRows([]));
  }, [categoryId, filters]);

  if (!rows.length) return null;
  const maxModels = Math.max(...rows.map((r) => r.model_count));

  return (
    <div className="rounded-xl bg-white shadow-sm border border-slate-100 overflow-hidden">
      <div className="px-4 py-2 border-b border-slate-100 flex items-center justify-between">
        <span className="text-sm font-semibold text-slate-600">
          {categoryName} 브랜드 비교 <span className="text-xs font-normal text-slate-400">· 부품 제외 · 전체 브랜드(필터 반영)</span>
        </span>
        <button
          onClick={() =>
            downloadCsv(
              `브랜드비교_${categoryName}.csv`,
              [
                { key: "brand", label: "브랜드" },
                { key: "is_own", label: "자사" },
                { key: "model_count", label: "모델수" },
                { key: "avg_price", label: "평균가" },
                { key: "min_price", label: "최저가" },
                { key: "median_change_pct", label: "변동률(%)" },
              ],
              rows
            )
          }
          className={csvBtnClass}
        >
          ⬇ CSV
        </button>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-slate-500 text-xs">
            <tr>
              <th className="text-left px-3 py-2">브랜드</th>
              <th className="text-left px-3 py-2 w-24">모델수</th>
              <th className="text-right px-3 py-2">평균가</th>
              <th className="text-right px-3 py-2">최저가</th>
              <th className="text-right px-3 py-2">변동</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr
                key={r.brand}
                className={`border-t border-slate-50 ${r.is_own ? "bg-own/5" : ""}`}
              >
                <td className="px-3 py-2 font-medium">
                  {r.is_own && <span className="text-own mr-1">★</span>}
                  {r.brand}
                </td>
                <td className="px-3 py-2">
                  <div className="flex items-center gap-1.5">
                    <div className="h-2 rounded bg-slate-100 flex-1 max-w-[60px] overflow-hidden">
                      <div
                        className={r.is_own ? "bg-own h-full" : "bg-slate-300 h-full"}
                        style={{ width: `${(r.model_count / maxModels) * 100}%` }}
                      />
                    </div>
                    <span className="text-xs text-slate-400">{r.model_count}</span>
                  </div>
                </td>
                <td className="px-3 py-2 text-right">{won(r.avg_price)}</td>
                <td className="px-3 py-2 text-right text-slate-500">{won(r.min_price)}</td>
                <td className={`px-3 py-2 text-right font-medium ${changeColor(r.median_change_pct)}`}>
                  {pct(r.median_change_pct)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
