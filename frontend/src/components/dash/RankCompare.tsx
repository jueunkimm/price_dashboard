import { useEffect, useMemo, useState } from "react";
import { api, type RankingRow, type Timeseries } from "../../api";
import { won, pct } from "../../format";
import { PALETTE, chgColor, synthTrend } from "./util";
import Spark from "./Spark";

// 디자인 핸드오프 — 좌: 가격 변동 랭킹(클릭→비교 추가), 우: 제품 비교(지수 정규화).
// 실제 시계열(timeseriesAll)을 우선 사용, 없으면 변동률 기반 합성 추세로 폴백.
const MAX = 5;

export default function RankCompare({ rows, q }: { rows: RankingRow[]; q: string }) {
  const [tsMap, setTsMap] = useState<Record<string, Timeseries>>({});
  const [rankFilter, setRankFilter] = useState<"all" | "cuckoo">("all");
  const [compare, setCompare] = useState<number[]>([]); // product_id, 최대 5

  useEffect(() => {
    api.timeseriesAll().then(setTsMap).catch(() => setTsMap({}));
  }, []);

  // 실제 시계열(>=2) 우선, 없으면 합성 추세
  const trendOf = (r: RankingRow): number[] => {
    const s = tsMap[String(r.product_id)]?.series;
    if (s && s.length >= 2) return s.map((p) => p.price);
    return synthTrend(r.change_pct, 14, r.product_id);
  };

  const filtered = useMemo(() => {
    const qq = q.trim();
    return rows.filter((r) => {
      if (rankFilter === "cuckoo" && !r.is_own_brand) return false;
      if (qq && !r.model_name.includes(qq) && !r.category_name.includes(qq)) return false;
      return true;
    });
  }, [rows, rankFilter, q]);

  const toggle = (id: number) =>
    setCompare((c) => {
      if (c.includes(id)) return c.filter((x) => x !== id);
      if (c.length >= MAX) return c;
      return [...c, id];
    });
  const colorOf = (id: number) => {
    const i = compare.indexOf(id);
    return i >= 0 ? PALETTE[i % PALETTE.length] : null;
  };

  // 비교 지수 차트: 각 선택 추세를 시작값=100 정규화 후 공통 min/max로 스케일
  const lines = useMemo(() => {
    const sel = compare
      .map((id) => {
        const r = rows.find((x) => x.product_id === id);
        return r ? { id, r, vals: trendOf(r) } : null;
      })
      .filter(Boolean) as { id: number; r: RankingRow; vals: number[] }[];
    const norm = sel.map((x) => {
      const b = x.vals[0] || 1;
      return { ...x, idx: x.vals.map((v) => (v / b) * 100) };
    });
    const all = norm.flatMap((x) => x.idx);
    if (!all.length) return [];
    const mn = Math.min(...all);
    const mx = Math.max(...all);
    const rng = mx - mn || 1;
    const W = 280;
    const H = 96;
    const p = 8;
    return norm.map((x, i) => ({
      id: x.id,
      r: x.r,
      color: PALETTE[i % PALETTE.length],
      points: x.idx
        .map((v, j) => {
          const xx = (j / (x.idx.length - 1)) * (W - p * 2) + p;
          const yy = H - p - ((v - mn) / rng) * (H - p * 2);
          return `${xx.toFixed(1)},${yy.toFixed(1)}`;
        })
        .join(" "),
    }));
  }, [compare, rows, tsMap]);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-[1.7fr_1fr] gap-[18px] items-start">
      {/* ── 좌: 가격 변동 랭킹 ── */}
      <div className="bg-white border border-[#e9e9ee] rounded-[14px] overflow-hidden min-w-0">
        <div className="px-[18px] pt-4 pb-3 border-b border-[#f0f0f3] flex items-center justify-between flex-wrap gap-2">
          <div className="flex items-baseline gap-2">
            <span className="text-[15px] font-bold">가격 변동 랭킹</span>
            <span className="text-xs text-[#9a9aa2]">행을 클릭해 비교에 추가</span>
          </div>
          <div className="flex gap-1.5">
            {(["all", "cuckoo"] as const).map((k) => (
              <button
                key={k}
                onClick={() => setRankFilter(k)}
                className={`px-3 py-1.5 rounded-lg text-[13px] font-semibold ${
                  rankFilter === k ? "bg-ink text-white" : "bg-[#f0f0f3] text-[#6b6b73]"
                }`}
              >
                {k === "all" ? "전체" : "쿠쿠"}
              </button>
            ))}
          </div>
        </div>
        <div className="grid grid-cols-[34px_1fr_96px_92px_84px] gap-2 px-[18px] py-2.5 text-[11px] font-semibold text-[#9a9aa2] border-b border-[#f0f0f3]">
          <div>#</div>
          <div>제품</div>
          <div className="text-right">현재가</div>
          <div className="text-right">변동률</div>
          <div className="text-right">추세</div>
        </div>
        <div className="max-h-[520px] overflow-y-auto">
          {filtered.length === 0 ? (
            <div className="py-12 text-center text-sm text-[#aaaab2]">조건에 맞는 제품이 없습니다.</div>
          ) : (
            filtered.map((r, idx) => {
              const col = colorOf(r.product_id);
              const on = col != null;
              const cc = chgColor(r.change_pct);
              return (
                <div
                  key={r.product_id}
                  onClick={() => toggle(r.product_id)}
                  className="grid grid-cols-[34px_1fr_96px_92px_84px] gap-2 px-[18px] py-3 items-center border-b border-[#f4f4f6] cursor-pointer hover:bg-[#f8f8fb]"
                  style={on ? { background: "#f5f5fd", boxShadow: `inset 3px 0 0 ${col}` } : undefined}
                >
                  <div className="text-[13px] font-bold text-[#bcbcc4]">{idx + 1}</div>
                  <div className="min-w-0">
                    <div className="flex items-center gap-1.5">
                      {r.is_own_brand && (
                        <span className="text-[10px] font-bold text-[#4b47c4] bg-[#ecebfb] px-1.5 py-0.5 rounded-[5px] shrink-0">
                          쿠쿠
                        </span>
                      )}
                      <span className="text-[13px] font-semibold truncate">{r.model_name}</span>
                      {/* 상품 링크(있으면 상품페이지 ↗, 없으면 네이버쇼핑 검색 ⌕). 행 클릭(비교추가)과 분리 */}
                      <a
                        href={
                          r.link ||
                          `https://search.shopping.naver.com/search/all?query=${encodeURIComponent(r.model_name)}`
                        }
                        target="_blank"
                        rel="noopener noreferrer"
                        onClick={(e) => e.stopPropagation()}
                        title={r.link ? "네이버 상품 페이지 열기" : "네이버 쇼핑에서 검색"}
                        className="shrink-0 text-[#bcbcc4] hover:text-own text-[13px] leading-none"
                      >
                        {r.link ? "↗" : "⌕"}
                      </a>
                    </div>
                    <div className="text-[11px] text-[#9a9aa2] mt-0.5">{r.category_name}</div>
                  </div>
                  <div className="text-right text-[13px] font-bold tabular-nums">{won(r.current_price)}</div>
                  <div className="text-right text-[13px] font-bold tabular-nums" style={{ color: cc }}>
                    {pct(r.change_pct)}
                  </div>
                  <div className="flex justify-end">
                    <Spark vals={trendOf(r).slice(-14)} color={cc} />
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* ── 우: 제품 비교 ── */}
      <div className="bg-white border border-[#e9e9ee] rounded-[14px] p-[18px] lg:sticky lg:top-[120px]">
        <div className="flex items-center justify-between mb-1">
          <span className="text-[15px] font-bold">제품 비교</span>
          <span className="text-xs text-[#9a9aa2]">{compare.length} / 5</span>
        </div>
        <div className="text-[11px] text-[#9a9aa2] mb-3.5">시작 시점 = 100 지수로 추세 비교</div>
        {compare.length === 0 ? (
          <div className="border-[1.5px] border-dashed border-[#e2e2e8] rounded-[11px] py-[34px] px-4 text-center text-[#aaaab2] text-[13px] leading-relaxed">
            왼쪽 랭킹에서 제품을 클릭해
            <br />
            비교에 추가하세요 (최대 5개)
          </div>
        ) : (
          <>
            <div className="border border-[#f0f0f3] rounded-[11px] p-2.5 bg-[#fafafb] mb-3">
              <svg width="100%" height="96" viewBox="0 0 280 96" preserveAspectRatio="none" className="block">
                <line x1="6" y1="51" x2="274" y2="51" stroke="#e4e4ea" strokeWidth="1" strokeDasharray="3 3" />
                {lines.map((l) => (
                  <polyline
                    key={l.id}
                    points={l.points}
                    fill="none"
                    stroke={l.color}
                    strokeWidth="1.8"
                    strokeLinejoin="round"
                    strokeLinecap="round"
                  />
                ))}
              </svg>
            </div>
            <div className="flex flex-col gap-[7px]">
              {lines.map((l) => (
                <div key={l.id} className="flex items-center gap-2">
                  <span className="w-[9px] h-[9px] rounded-[3px] shrink-0" style={{ background: l.color }} />
                  <div className="flex-1 min-w-0">
                    <div className="text-[12px] font-semibold truncate">{l.r.model_name}</div>
                  </div>
                  <span className="text-[12px] font-bold tabular-nums" style={{ color: chgColor(l.r.change_pct) }}>
                    {pct(l.r.change_pct)}
                  </span>
                  <button
                    onClick={() => toggle(l.id)}
                    className="text-[14px] text-[#bcbcc4] px-0.5 hover:text-[#6b6b73]"
                  >
                    ×
                  </button>
                </div>
              ))}
              <button
                onClick={() => setCompare([])}
                className="mt-1.5 text-[12px] text-[#8e8e99] text-center py-1.5 rounded-[7px] bg-[#f4f4f6] hover:bg-[#ececf0]"
              >
                전체 비교 초기화
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
