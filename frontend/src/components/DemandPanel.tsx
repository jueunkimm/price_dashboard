import { useEffect, useMemo, useState } from "react";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api, type Demand } from "../api";

// 시계열의 '최근 N일 평균 vs 직전 N일 평균' 변화율(%) — WoW(7)·MoM(30) 계산용
function periodChange(series: { date: string; ratio: number }[], n: number): number | null {
  if (series.length < n * 2) return null;
  const s = [...series].sort((a, b) => a.date.localeCompare(b.date));
  const recent = s.slice(-n);
  const prior = s.slice(-n * 2, -n);
  const avg = (a: typeof s) => a.reduce((x, p) => x + p.ratio, 0) / a.length;
  const pr = avg(prior);
  if (!pr) return null;
  return Math.round(((avg(recent) - pr) / pr) * 1000) / 10;
}

// 수요 트렌드(F7) — 검색 관심도(통합검색) + 쇼핑 클릭(쇼핑인사이트)
// ⑤ 기간비교(WoW/MoM) + ② 수요×가격 신호
export default function DemandPanel({
  categoryId,
  categoryName,
  priceChange,
}: {
  categoryId: number;
  categoryName: string;
  priceChange?: number | null; // 카테고리 중앙값 변동률(%) — 수요×가격 신호용
}) {
  const [data, setData] = useState<Demand | null>(null);
  const [showHelp, setShowHelp] = useState(false);

  useEffect(() => {
    api.demand(categoryId).then(setData).catch(() => setData(null));
  }, [categoryId]);

  // 날짜 기준으로 두 신호 병합
  const merged = useMemo(() => {
    if (!data) return [];
    const map = new Map<string, { date: string; search?: number; shopping?: number }>();
    for (const p of data.search) map.set(p.date, { date: p.date, search: p.ratio });
    for (const p of data.shopping) {
      const row = map.get(p.date) ?? { date: p.date };
      row.shopping = p.ratio;
      map.set(p.date, row);
    }
    return [...map.values()].sort((a, b) => a.date.localeCompare(b.date));
  }, [data]);

  // ⑤ 기간비교(WoW/MoM) + ② 수요×가격 신호 — 쇼핑클릭(구매의도) 우선
  const sig = useMemo(() => {
    if (!data) return null;
    const dSeries = data.shopping.length >= 14 ? data.shopping : data.search;
    const wow = periodChange(dSeries, 7);
    const mom = periodChange(dSeries, 30);
    const dMom = mom ?? wow ?? 0;
    const dUp = dMom > 5, dDown = dMom < -5;
    const pUp = (priceChange ?? 0) > 1, pDown = (priceChange ?? 0) < -1;
    let label = "보합", tone = "slate", desc = "수요·가격 큰 변화 없음";
    if (dUp && pDown) { label = "🟢 기회"; tone = "emerald"; desc = "수요 상승 + 가격 하락 — 적극 대응 구간"; }
    else if (dUp && pUp) { label = "🔵 강세"; tone = "blue"; desc = "수요·가격 동반 상승 — 프리미엄 여력"; }
    else if (dUp) { label = "🔵 수요 상승"; tone = "blue"; desc = "수요 상승 — 주목"; }
    else if (dDown) { label = "🔴 주의"; tone = "rose"; desc = "수요 냉각 — 재고·신제품 타이밍 주의"; }
    return { wow, mom, dUp, dDown, label, tone, desc };
  }, [data, priceChange]);

  if (!data || merged.length === 0) return null;
  const synthetic = data.is_synthetic;
  const toneCls: Record<string, string> = {
    emerald: "bg-emerald-50 text-emerald-700 border-emerald-200",
    blue: "bg-blue-50 text-blue-700 border-blue-200",
    rose: "bg-rose-50 text-rose-700 border-rose-200",
    slate: "bg-slate-50 text-slate-600 border-slate-200",
  };
  const chgCls = (v: number | null | undefined) =>
    v == null ? "text-slate-400" : v > 0 ? "text-emerald-600" : v < 0 ? "text-rose-500" : "text-slate-500";
  const fmt = (v: number | null | undefined) => (v == null ? "—" : `${v > 0 ? "+" : ""}${v}%`);

  return (
    <div className="rounded-xl bg-white p-4 shadow-sm border border-slate-100">
      <div className="flex items-center justify-between mb-1">
        <div className="font-semibold text-sm flex items-center gap-1.5">
          {categoryName} 수요 트렌드
          <button
            onClick={() => setShowHelp((v) => !v)}
            className={`w-4 h-4 inline-flex items-center justify-center rounded-full text-[10px] font-bold border ${
              showHelp ? "bg-slate-700 text-white border-slate-700" : "text-slate-400 border-slate-300"
            }`}
            title="두 그래프 해석 도움말"
          >
            i
          </button>
        </div>
        <span className="text-[10px] text-slate-400">상대지수 0~100</span>
      </div>
      <div className="text-[11px] text-slate-400 mb-2">
        검색=통합검색 관심도 · 쇼핑=네이버쇼핑 클릭(구매의도 근접)
      </div>

      {/* ⑤ 기간비교 + ② 수요×가격 신호 */}
      {sig && (
        <div className="flex flex-wrap items-center gap-2 mb-3">
          <span className={`text-xs font-semibold px-2 py-1 rounded-lg border ${toneCls[sig.tone]}`} title={sig.desc}>
            {sig.label}
          </span>
          <span className="text-[11px] text-slate-500">
            수요 WoW <b className={chgCls(sig.wow)}>{fmt(sig.wow)}</b>
          </span>
          <span className="text-[11px] text-slate-500">
            MoM <b className={chgCls(sig.mom)}>{fmt(sig.mom)}</b>
          </span>
          {priceChange != null && (
            <span className="text-[11px] text-slate-500">
              가격 <b className={chgCls(priceChange)}>{fmt(priceChange)}</b>
            </span>
          )}
          <span className="text-[11px] text-slate-400 w-full">{sig.desc}</span>
        </div>
      )}

      {showHelp && (
        <div className="mb-3 rounded-lg bg-slate-50 border border-slate-100 p-3 text-[11px] text-slate-600 space-y-2">
          <div>
            <b className="text-emerald-600">🟢 검색 관심도</b> = 통합검색에서 검색한 양(정보탐색 포함, 폭넓은 관심) ·{" "}
            <b className="text-own">🟣 쇼핑 클릭</b> = 네이버쇼핑 클릭(구매의도에 더 근접)
          </div>
          <div className="text-amber-600">
            ⚠ 두 선은 <b>각자 0~100으로 따로 정규화</b>됩니다 → 선의 <b>높이를 직접 비교하지 말고</b>, 각 추세와 둘의 어긋남을 보세요.
          </div>
          <div className="grid grid-cols-1 gap-0.5">
            <div>· 🟢↑ &nbsp;🟣 정체 → 관심만 늘고 구매는 안 따라옴(탐색 단계)</div>
            <div>· 🟣↑ &nbsp;🟢 정체 → <b className="text-own">구매 클릭이 먼저 튐(매수 임박, 주목)</b></div>
            <div>· 🟢🟣 동반↑ → 건강한 수요 상승 · 동반↓ → 수요 냉각</div>
            <div className="text-slate-500">
              결합: <b>가격↓ + 🟣↑</b> = 적극 대응 구간 / <b>가격↓ + 🟣 정체</b> = 안 팔려 내리는 것
            </div>
          </div>
        </div>
      )}
      <ResponsiveContainer width="100%" height={190}>
        <LineChart data={merged} margin={{ left: -8, right: 4, top: 4 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
          <XAxis dataKey="date" tick={{ fontSize: 10 }} minTickGap={30} />
          <YAxis tick={{ fontSize: 10 }} domain={[0, 100]} />
          <Tooltip />
          <Legend wrapperStyle={{ fontSize: 11 }} />
          <Line
            type="monotone"
            dataKey="search"
            name="검색 관심도"
            stroke="#10b981"
            strokeWidth={2}
            dot={false}
            connectNulls
          />
          <Line
            type="monotone"
            dataKey="shopping"
            name="쇼핑 클릭"
            stroke="#7c3aed"
            strokeWidth={2}
            dot={false}
            connectNulls
          />
        </LineChart>
      </ResponsiveContainer>
      {synthetic && (
        <div className="text-[11px] text-amber-600 mt-1">
          ⚠ 데모용 합성 데이터. 네이버 데이터랩 권한 추가 후 실데이터로 교체됩니다.
        </div>
      )}
    </div>
  );
}
