import { useMemo } from "react";
import type { CategoryOverview } from "../api";
import { won, pct, changeColor, arrow } from "../format";

// 홈 최상단 '★ 쿠쿠 라인업 요약' — 쿠쿠 취급 카테고리를 한눈에.
// 변동 큰 순(급변·|변동률|)으로 정렬해 매일 먼저 봐야 할 카테고리를 앞에 둔다.
export default function OwnLineupSummary({
  cats,
  selectedId,
  onSelect,
}: {
  cats: CategoryOverview[];
  selectedId: number | null;
  onSelect: (c: CategoryOverview) => void;
}) {
  const own = useMemo(
    () =>
      cats
        .filter((c) => c.has_own_lineup)
        .sort(
          (a, b) =>
            b.anomaly_count - a.anomaly_count ||
            Math.abs(b.median_change_pct ?? 0) - Math.abs(a.median_change_pct ?? 0)
        ),
    [cats]
  );

  if (!own.length) return null;

  const movers = own.filter((c) => c.anomaly_count > 0).length;

  return (
    <section className="rounded-xl border border-own/30 bg-own/[0.03] p-4">
      <div className="flex items-center justify-between gap-2 mb-3">
        <h2 className="text-sm font-bold text-own flex items-center gap-1.5">
          ★ 쿠쿠 라인업 요약
          <span className="text-[11px] font-normal text-slate-400">
            취급 {own.length}개 카테고리{movers > 0 && ` · 급변 ${movers}`}
          </span>
        </h2>
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2.5">
        {own.map((c) => (
          <button
            key={c.category_id}
            onClick={() => onSelect(c)}
            className={`text-left rounded-lg bg-white p-3 border transition hover:shadow-md ${
              selectedId === c.category_id ? "border-own ring-1 ring-own" : "border-own/15"
            }`}
          >
            <div className="flex items-center justify-between gap-1 mb-1">
              <span className="font-semibold text-xs truncate">{c.category_name}</span>
              {c.anomaly_count > 0 && (
                <span className="text-[9px] bg-up/10 text-up px-1 py-0.5 rounded shrink-0">급변</span>
              )}
            </div>
            <div className="text-sm font-bold tabular-nums">{won(c.median_price)}</div>
            <div className={`text-xs font-medium ${changeColor(c.median_change_pct)}`}>
              {arrow(c.median_change_pct)} {pct(c.median_change_pct)}
            </div>
          </button>
        ))}
      </div>
    </section>
  );
}
