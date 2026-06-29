import { useEffect, useMemo, useState } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api, type RankingRow, type Timeseries } from "../api";
import { won, pct, changeColor, arrow } from "../format";

// 디자인 핸드오프(방향 A · 비교 워크벤치): 좌측 고밀도 변동 랭킹 + 우측 다중 제품 비교.
// 행을 클릭하면 해당 제품을 비교에 추가/제거(최대 5). 가격대가 달라도 비교되도록
// 각 제품 시계열을 '첫 값 = 100 지수'로 정규화해 추세를 겹쳐 본다.
const PALETTE = ["#4f46e5", "#0d9488", "#d97706", "#7c3aed", "#0891b2"];
const MAX_SEL = 5;

function Spark({ vals, color, w = 64, h = 22 }: { vals: number[]; color: string; w?: number; h?: number }) {
  if (vals.length < 2) return <svg width={w} height={h} />;
  const mn = Math.min(...vals);
  const mx = Math.max(...vals);
  const r = mx - mn || 1;
  const pad = 2;
  const pts = vals
    .map((v, i) => {
      const x = pad + (w - 2 * pad) * (i / (vals.length - 1));
      const y = h - pad - (h - 2 * pad) * ((v - mn) / r);
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
  return (
    <svg width={w} height={h} className="overflow-visible">
      <polyline points={pts} fill="none" stroke={color} strokeWidth="1.6" strokeLinejoin="round" strokeLinecap="round" />
    </svg>
  );
}

export default function CompareWorkbench({
  rows,
  onOpenDetail,
}: {
  rows: RankingRow[];
  onOpenDetail: (productId: number) => void;
}) {
  const [tsMap, setTsMap] = useState<Record<string, Timeseries>>({});
  const [selected, setSelected] = useState<number[]>([]);
  const [sort, setSort] = useState<{ key: "name" | "cat" | "price" | "chg"; dir: "asc" | "desc" } | null>(null);
  const [catFilter, setCatFilter] = useState<string>(""); // "" = 전체 카테고리

  // 랭킹에 등장하는 카테고리 목록(가나다순) — 카테고리별 비교용 드롭다운
  const catList = useMemo(
    () => Array.from(new Set(rows.map((r) => r.category_name).filter(Boolean))).sort((a, b) => a.localeCompare(b, "ko")),
    [rows]
  );

  const clickSort = (key: "name" | "cat" | "price" | "chg") =>
    setSort((s) =>
      s?.key === key ? { key, dir: s.dir === "asc" ? "desc" : "asc" } : { key, dir: key === "chg" ? "desc" : "asc" }
    );
  const sortArrow = (key: string) =>
    sort?.key === key ? <span className="text-own ml-0.5">{sort.dir === "asc" ? "▲" : "▼"}</span> : null;
  const sortedRows = useMemo(() => {
    const base = catFilter ? rows.filter((r) => r.category_name === catFilter) : rows;
    if (!sort) return base;
    const dir = sort.dir === "asc" ? 1 : -1;
    return [...base].sort((a, b) => {
      if (sort.key === "cat") {
        // 카테고리 그룹(방향 토글) 1차, 동일 카테고리 내 변동률 큰 순 2차
        const cc = a.category_name.localeCompare(b.category_name, "ko");
        if (cc !== 0) return cc * dir;
        return (b.change_pct ?? -Infinity) - (a.change_pct ?? -Infinity);
      }
      let c = 0;
      if (sort.key === "name") c = a.model_name.localeCompare(b.model_name, "ko");
      else if (sort.key === "price") c = a.current_price - b.current_price;
      else c = (a.change_pct ?? -Infinity) - (b.change_pct ?? -Infinity);
      return c * dir;
    });
  }, [rows, sort, catFilter]);

  useEffect(() => {
    api.timeseriesAll().then(setTsMap).catch(() => setTsMap({}));
  }, []);

  const toggle = (id: number) =>
    setSelected((s) => {
      if (s.includes(id)) return s.filter((x) => x !== id);
      if (s.length >= MAX_SEL) return s;
      return [...s, id];
    });

  const colorOf = (id: number) => {
    const i = selected.indexOf(id);
    return i >= 0 ? PALETTE[i % PALETTE.length] : null;
  };

  // 비교 차트 데이터: 선택 제품을 첫 값=100 지수로 정규화 후 날짜로 병합
  const { chartData, legend } = useMemo(() => {
    const sel = selected.map((id) => ({ id, ts: tsMap[String(id)] })).filter((x) => x.ts?.series?.length);
    const dates = Array.from(new Set(sel.flatMap((x) => x.ts.series.map((p) => p.date)))).sort();
    const normByDate: Record<number, Record<string, number>> = {};
    sel.forEach(({ id, ts }) => {
      const base = ts.series[0]?.price || 1;
      const m: Record<string, number> = {};
      ts.series.forEach((p) => (m[p.date] = Math.round((p.price / base) * 1000) / 10));
      normByDate[id] = m;
    });
    const data = dates.map((d) => {
      const row: Record<string, number | string | null> = { date: d.slice(5) };
      sel.forEach(({ id }) => (row["p" + id] = normByDate[id][d] ?? null));
      return row;
    });
    const leg = sel.map(({ id, ts }) => {
      const row = rows.find((r) => r.product_id === id);
      const first = ts.series[0]?.price ?? 0;
      const last = ts.series[ts.series.length - 1]?.price ?? 0;
      const chg = first ? ((last - first) / first) * 100 : 0;
      const lo = Math.min(...ts.series.map((p) => p.price));
      return {
        id,
        color: colorOf(id) ?? "#999",
        name: row?.model_name ?? ts.model_name,
        cat: row?.category_name ?? "",
        price: last,
        lo,
        chg,
      };
    });
    return { chartData: data, legend: leg };
  }, [selected, tsMap, rows]);

  if (!rows.length)
    return <div className="text-slate-400 text-sm py-8 text-center">변동 데이터가 없습니다.</div>;

  return (
    <div className="grid lg:grid-cols-[1fr_minmax(0,540px)] gap-5">
      {/* ── 좌: 변동 랭킹 (체크박스로 비교 선택) ── */}
      <div className="rounded-xl bg-white border border-slate-100 shadow-sm min-w-0">
        <div className="flex items-center gap-2 px-3 py-2 border-b border-slate-50 flex-wrap">
          <span className="text-sm font-semibold text-slate-700">가격 변동 랭킹</span>
          <span className="text-[11px] text-slate-400">{sortedRows.length}개 · 행 클릭 → 비교 추가</span>
          <div className="ml-auto flex items-center gap-1.5">
            <select
              value={catFilter}
              onChange={(e) => setCatFilter(e.target.value)}
              className="text-[11px] text-slate-600 border border-slate-200 rounded px-1.5 py-1 bg-white max-w-[9rem] focus:outline-none focus:ring-1 focus:ring-own/40"
              title="카테고리로 필터"
            >
              <option value="">전체 카테고리</option>
              {catList.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
            <button
              onClick={() => clickSort("cat")}
              className={`text-[11px] rounded px-1.5 py-1 border ${
                sort?.key === "cat"
                  ? "border-own text-own bg-own/5"
                  : "border-slate-200 text-slate-500 hover:text-slate-700"
              }`}
              title="카테고리별로 묶어 정렬(같은 카테고리는 변동 큰 순)"
            >
              카테고리순{sortArrow("cat")}
            </button>
          </div>
        </div>
        <div className="grid grid-cols-[28px_1fr_104px_84px_64px] gap-2 px-3 py-1.5 bg-slate-50/70 border-b border-slate-100 text-[11px] font-semibold text-slate-400 select-none">
          <div />
          <div className="cursor-pointer hover:text-slate-600" onClick={() => clickSort("name")}>
            제품{sortArrow("name")}
          </div>
          <div className="text-right cursor-pointer hover:text-slate-600" onClick={() => clickSort("price")}>
            현재가{sortArrow("price")}
          </div>
          <div className="text-right cursor-pointer hover:text-slate-600" onClick={() => clickSort("chg")}>
            변동{sortArrow("chg")}
          </div>
          <div className="text-right">추세</div>
        </div>
        <div className="max-h-[30rem] overflow-auto rounded-b-xl">
          {sortedRows.map((r) => {
            const col = colorOf(r.product_id);
            const on = col != null;
            const ts = tsMap[String(r.product_id)];
            const sparkVals = (ts?.series ?? []).slice(-8).map((p) => p.price);
            return (
              <div
                key={r.product_id}
                onClick={() => toggle(r.product_id)}
                className="grid grid-cols-[28px_1fr_104px_84px_64px] gap-2 px-3 py-2 border-b border-slate-50 cursor-pointer hover:bg-slate-50 items-center"
                style={on ? { background: "#f6f7ff", boxShadow: `inset 3px 0 0 ${col}` } : undefined}
              >
                <div className="flex items-center justify-center">
                  <span
                    className="w-[17px] h-[17px] rounded-[5px] flex items-center justify-center text-white text-[11px] font-bold border"
                    style={on ? { background: col!, borderColor: col! } : { borderColor: "#cfd3db", borderWidth: 1.5 }}
                  >
                    {on ? "✓" : ""}
                  </span>
                </div>
                <div className="min-w-0">
                  <div className="text-[13px] font-medium text-slate-800 truncate">
                    {r.is_own_brand && <span className="text-[10px] bg-own/10 text-own px-1 py-0.5 rounded mr-1">쿠쿠</span>}
                    {r.is_rental && <span className="text-[10px] bg-amber-100 text-amber-700 px-1 py-0.5 rounded mr-1">렌탈</span>}
                    {r.model_name}
                  </div>
                  <div className="text-[10px] text-slate-400 truncate">{r.category_name}</div>
                </div>
                <div className="text-right text-[13px] font-mono tabular-nums text-slate-800">{won(r.current_price)}</div>
                <div className={`text-right text-[12px] font-mono tabular-nums font-medium ${changeColor(r.change_pct)}`}>
                  {arrow(r.change_pct)} {pct(r.change_pct)}
                </div>
                <div className="flex justify-end">
                  <Spark vals={sparkVals} color={changeColor(r.change_pct) === "text-up" ? "#dc2626" : changeColor(r.change_pct) === "text-down" ? "#2563eb" : "#9aa0aa"} />
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* ── 우: 다중 제품 비교 (지수 정규화) ── */}
      <div className="rounded-xl bg-white border border-slate-100 shadow-sm min-w-0 flex flex-col">
        <div className="flex items-center gap-2 px-4 py-2.5 border-b border-slate-50 flex-wrap">
          <span className="text-sm font-semibold text-slate-700">제품 비교</span>
          <span className="text-[11px] font-medium text-own bg-own/10 px-2 py-0.5 rounded">{selected.length}개 선택</span>
          {selected.length > 0 && (
            <button
              onClick={() => setSelected([])}
              className="text-[11px] text-slate-400 hover:text-rose-500 hover:underline"
              title="선택한 제품 전체 해제"
            >
              전체 해제
            </button>
          )}
          <span className="ml-auto text-[11px] text-slate-400">첫 값=100 지수 · 가격대 달라도 추세 비교</span>
        </div>
        <div className="px-2 pt-3">
          {legend.length === 0 ? (
            <div className="h-56 flex items-center justify-center text-slate-400 text-sm">
              좌측 랭킹에서 제품을 클릭해 비교에 추가하세요.
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={224}>
              <LineChart data={chartData} margin={{ top: 6, right: 12, bottom: 0, left: -8 }}>
                <CartesianGrid stroke="#eceef2" vertical={false} />
                <XAxis dataKey="date" tick={{ fontSize: 10, fill: "#aeb4bf" }} interval="preserveStartEnd" minTickGap={28} />
                <YAxis tick={{ fontSize: 10, fill: "#aeb4bf" }} width={34} domain={["auto", "auto"]} />
                <Tooltip
                  contentStyle={{ fontSize: 12, borderRadius: 8, border: "1px solid #e6e8ee" }}
                  formatter={(v: number) => [`${v} (지수)`, ""]}
                />
                {legend.map((l) => (
                  <Line
                    key={l.id}
                    type="monotone"
                    dataKey={"p" + l.id}
                    stroke={l.color}
                    strokeWidth={2.2}
                    dot={false}
                    connectNulls
                    isAnimationActive={false}
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>
        {/* 비교 표 */}
        <div className="px-3 pb-2 mt-1">
          {legend.map((l) => (
            <div
              key={l.id}
              onClick={() => onOpenDetail(l.id)}
              className="grid grid-cols-[12px_1fr_92px_64px] gap-2.5 items-center py-2 border-t border-slate-50 cursor-pointer hover:bg-slate-50 rounded"
            >
              <span className="w-[11px] h-[11px] rounded-[3px]" style={{ background: l.color }} />
              <div className="min-w-0">
                <div className="text-[12px] font-medium text-slate-800 truncate">{l.name}</div>
                <div className="text-[10px] text-slate-400 truncate">
                  {l.cat} · 최저 {won(l.lo)}
                </div>
              </div>
              <div className="text-right text-[13px] font-mono tabular-nums text-slate-800">{won(l.price)}</div>
              <div className={`text-right text-[12px] font-mono tabular-nums ${l.chg > 0.3 ? "text-up" : l.chg < -0.3 ? "text-down" : "text-slate-400"}`}>
                {l.chg >= 0 ? "+" : ""}
                {l.chg.toFixed(1)}%
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
