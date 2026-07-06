import { useEffect, useState } from "react";
import { api, type CategoryOverview, type RankingRow, type WeeklyReport } from "../../api";
import { C } from "./util";
import RankCompare from "./RankCompare";
import CategoryTable from "./CategoryTable";

// 디자인 핸드오프 — 시장 현황 개요: 주간요약 + 랭킹/비교 + 카테고리표
// (상세 필터 카드는 FilterCard로 분리되어 App에서 전체현황·상세뷰 공용으로 렌더)
export default function MarketTab({
  cats,
  ranking,
  q,
  onPickCategory,
}: {
  cats: CategoryOverview[];
  ranking: RankingRow[];
  q: string;
  onPickCategory: (categoryId: number) => void;
}) {
  const [weekly, setWeekly] = useState<WeeklyReport | null>(null);

  useEffect(() => {
    api.report().then(setWeekly).catch(() => setWeekly(null));
  }, []);

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
