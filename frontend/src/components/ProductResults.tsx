import { useEffect, useMemo, useState } from "react";
import { api, type FilteredProduct, type ProductFilters } from "../api";
import { won, pct, changeColor } from "../format";
import { downloadCsv, csvBtnClass } from "../csv";

// 필터된 제품 결과 테이블 — 사이드바 필터 + 헤더 쿠쿠 토글 반영
export default function ProductResults({
  filters,
  ownOnly,
  onSelect,
}: {
  filters: ProductFilters;
  ownOnly: boolean;
  onSelect: (productId: number) => void;
}) {
  const [rows, setRows] = useState<FilteredProduct[]>([]);
  const [loading, setLoading] = useState(false);

  // 현재 필터 결과의 가격 요약(평균·중앙값·최저·최고)
  const stat = useMemo(() => {
    const prices = rows.map((r) => r.current_price).sort((a, b) => a - b);
    if (!prices.length) return null;
    const sum = prices.reduce((a, b) => a + b, 0);
    const mid = Math.floor(prices.length / 2);
    const median = prices.length % 2 ? prices[mid] : (prices[mid - 1] + prices[mid]) / 2;
    return {
      count: prices.length,
      avg: Math.round(sum / prices.length),
      median: Math.round(median),
      min: prices[0],
      max: prices[prices.length - 1],
    };
  }, [rows]);

  useEffect(() => {
    setLoading(true);
    // 브랜드를 명시적으로 고르면 그 선택이 "쿠쿠만 보기" 토글보다 우선(충돌 방지).
    const ownEffective = (ownOnly || !!filters.own_only) && !filters.brand_id;
    api
      .productSearch({ ...filters, own_only: ownEffective })
      .then(setRows)
      .catch(() => setRows([]))
      .finally(() => setLoading(false));
  }, [filters, ownOnly]);

  return (
    <div className="rounded-xl bg-white border border-slate-100 shadow-sm">
      <div className="flex items-center justify-between px-3 py-1.5 border-b border-slate-50">
        <span className="text-xs text-slate-400">{loading ? "조회 중…" : `${rows.length}건`}</span>
        {rows.length > 0 && (
          <button
            onClick={() =>
              downloadCsv(
                "제품목록.csv",
                [
                  { key: "model_name", label: "모델명" },
                  { key: "brand", label: "브랜드" },
                  { key: "category_name", label: "카테고리" },
                  { key: "capacity_band", label: "용량" },
                  { key: "mall", label: "판매몰" },
                  { key: "current_price", label: "현재가" },
                  { key: "change_pct", label: "변동률(%)" },
                ],
                rows
              )
            }
            className={csvBtnClass}
          >
            ⬇ CSV
          </button>
        )}
      </div>

      {stat && (
        <div className="flex flex-wrap items-center gap-x-5 gap-y-1 px-3 py-2 bg-slate-50/70 border-b border-slate-100 text-sm">
          {filters.capacity_band && (
            <span className="text-xs font-semibold text-own">{filters.capacity_band}</span>
          )}
          <span className="text-slate-500">
            평균 <b className="text-slate-700">{won(stat.avg)}</b>
          </span>
          <span className="text-slate-500">
            중앙값 <b className="text-slate-700">{won(stat.median)}</b>
          </span>
          <span className="text-slate-400 text-xs">
            최저 {won(stat.min)} · 최고 {won(stat.max)} · {stat.count}개
          </span>
        </div>
      )}

      {rows.length === 0 ? (
        <div className="py-12 text-center text-slate-400 text-sm">
          {loading ? "불러오는 중…" : "조건에 맞는 제품이 없습니다."}
        </div>
      ) : (
        <div className="max-h-[60vh] overflow-auto rounded-b-xl">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-slate-500 text-xs sticky top-0 z-10">
            <tr>
              <th className="text-left px-3 py-2">제품</th>
              <th className="text-left px-3 py-2">브랜드</th>
              <th className="text-left px-3 py-2">용량</th>
              <th className="text-left px-3 py-2">판매몰</th>
              <th className="text-right px-3 py-2">현재가</th>
              <th className="text-right px-3 py-2">변동</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr
                key={r.product_id}
                onClick={() => onSelect(r.product_id)}
                className="border-t border-slate-50 hover:bg-slate-50 cursor-pointer"
              >
                <td className="px-3 py-2 max-w-xs truncate">
                  {r.is_own_brand && (
                    <span className="text-[10px] bg-own/10 text-own px-1 py-0.5 rounded mr-1">쿠쿠</span>
                  )}
                  {r.model_name}
                </td>
                <td className="px-3 py-2 text-slate-500">{r.brand}</td>
                <td className="px-3 py-2 text-slate-500">{r.capacity_band ?? "—"}</td>
                <td className="px-3 py-2">
                  {r.mall === "쿠팡" ? (
                    <span className="text-[11px] bg-rose-100 text-rose-600 px-1.5 py-0.5 rounded">쿠팡</span>
                  ) : (
                    <span className="text-slate-400 text-xs">{r.mall ?? "—"}</span>
                  )}
                </td>
                <td className="px-3 py-2 text-right">{won(r.current_price)}</td>
                <td className={`px-3 py-2 text-right font-medium ${changeColor(r.change_pct)}`}>
                  {pct(r.change_pct)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        </div>
      )}
    </div>
  );
}
