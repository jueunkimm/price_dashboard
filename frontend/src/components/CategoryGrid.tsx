import type { CategoryOverview } from "../api";
import { won, pct, changeColor, arrow } from "../format";

export default function CategoryGrid({
  cats,
  selectedId,
  onSelect,
}: {
  cats: CategoryOverview[];
  selectedId: number | null;
  onSelect: (c: CategoryOverview | null) => void;
}) {
  if (!cats.length)
    return (
      <div className="text-slate-400 text-sm py-8 text-center">
        데이터가 없습니다. 수집을 먼저 실행하세요 (collector.collect).
      </div>
    );
  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
      {cats.map((c) => (
        <div
          key={c.category_id}
          onClick={() => onSelect(selectedId === c.category_id ? null : c)}
          className={`rounded-xl bg-white p-4 shadow-sm border transition cursor-pointer hover:shadow-md ${
            selectedId === c.category_id
              ? "border-own ring-1 ring-own"
              : "border-slate-100"
          }`}
        >
          <div className="flex items-center justify-between mb-2">
            <span className="font-semibold text-sm">
              {c.has_own_lineup && <span className="text-own mr-1">★</span>}
              {c.category_name}
            </span>
            <span className="text-[11px] text-slate-400">{c.product_count}개</span>
          </div>
          <div className="text-lg font-bold">{won(c.median_price)}</div>
          <div className="text-[11px] text-slate-400">
            {won(c.min_price)} ~ {won(c.max_price)}
          </div>
          <div className={`mt-2 text-sm font-medium ${changeColor(c.median_change_pct)}`}>
            {arrow(c.median_change_pct)} {pct(c.median_change_pct)}
            {c.anomaly_count > 0 && (
              <span className="ml-2 text-[10px] bg-up/10 text-up px-1.5 py-0.5 rounded">
                급변 {c.anomaly_count}
              </span>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
