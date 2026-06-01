import { useEffect, useMemo, useState } from "react";
import {
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  CartesianGrid,
} from "recharts";
import { api, type Timeseries } from "../api";
import { won } from "../format";

const PERIODS = [
  { key: "7", label: "7일" },
  { key: "30", label: "30일" },
  { key: "90", label: "90일" },
  { key: "all", label: "전체" },
] as const;

export default function TrendChart({ productId }: { productId: number | null }) {
  const [data, setData] = useState<Timeseries | null>(null);
  const [loading, setLoading] = useState(false);
  const [period, setPeriod] = useState<string>("all");

  useEffect(() => {
    if (productId == null) {
      setData(null);
      return;
    }
    setLoading(true);
    api
      .timeseries(productId)
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [productId]);

  const series = useMemo(() => {
    const s = data?.series ?? [];
    if (period === "all") return s;
    return s.slice(-Number(period));
  }, [data, period]);

  if (productId == null)
    return (
      <div className="rounded-xl bg-white p-6 shadow-sm border border-slate-100 text-slate-400 text-sm text-center">
        랭킹·제품을 선택하면 가격 추세가 표시됩니다.
      </div>
    );

  return (
    <div className="rounded-xl bg-white p-4 shadow-sm border border-slate-100">
      <div className="flex items-center justify-between mb-3 gap-2">
        <div className="font-semibold text-sm truncate min-w-0">
          {data?.is_own_brand && <span className="text-own mr-1">쿠쿠</span>}
          {loading ? "불러오는 중…" : data?.model_name ?? ""}
        </div>
        <div className="flex gap-0.5 shrink-0">
          {PERIODS.map((p) => (
            <button
              key={p.key}
              onClick={() => setPeriod(p.key)}
              className={`text-[11px] px-1.5 py-0.5 rounded ${
                period === p.key ? "bg-slate-700 text-white" : "text-slate-400 hover:bg-slate-100"
              }`}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>

      {data && data.series.length < 2 ? (
        <div className="h-[260px] flex flex-col items-center justify-center text-center gap-1">
          <div className="text-slate-400 text-sm">변동 추세 데이터 수집 중</div>
          <div className="text-[11px] text-slate-400 max-w-xs">
            현재 {data.series.length}일치. 실수집이 2일 이상 누적되면 추세선이 그려집니다.
          </div>
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={260}>
          <LineChart data={series}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
            <XAxis dataKey="date" tick={{ fontSize: 11 }} minTickGap={24} />
            <YAxis tick={{ fontSize: 11 }} tickFormatter={(v) => `${(v / 10000).toFixed(0)}만`} />
            <Tooltip formatter={(v: number) => won(v)} />
            <Line
              type="monotone"
              dataKey="price"
              stroke={data?.is_own_brand ? "#7c3aed" : "#0ea5e9"}
              strokeWidth={2}
              dot={{ r: 2 }}
            />
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
