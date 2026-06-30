import { useEffect, useMemo, useState } from "react";
import { api, type Positioning } from "../../api";
import { won } from "../../format";
import { C, synthTrend } from "./util";
import Spark from "./Spark";

// 디자인 핸드오프 — 쿠쿠 분석 탭: 요약 카드 4 + 가격 포지셔닝 양방향 막대표
type SortKey = "name" | "cuckoo" | "market" | "pos" | "models";

export default function CuckooTab({ onPick }: { onPick: (categoryId: number) => void }) {
  const [pos, setPos] = useState<Positioning[]>([]);
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<"all" | "cheaper" | "pricier">("all");
  const [sort, setSort] = useState<{ key: SortKey; dir: "asc" | "desc" }>({ key: "pos", dir: "asc" });

  useEffect(() => {
    api.positioning().then(setPos).catch(() => setPos([]));
  }, []);

  const clickSort = (key: SortKey) =>
    setSort((s) =>
      s.key === key ? { key, dir: s.dir === "asc" ? "desc" : "asc" } : { key, dir: key === "name" || key === "pos" ? "asc" : "desc" }
    );
  const arr = (key: SortKey) => (sort.key === key ? (sort.dir === "asc" ? " ▲" : " ▼") : "");

  const summary = useMemo(() => {
    const valid = pos.filter((p) => p.positioning_pct != null);
    const cheaper = valid.filter((p) => (p.positioning_pct as number) < 0).length;
    const avg = valid.length
      ? valid.reduce((a, p) => a + (p.positioning_pct as number), 0) / valid.length
      : 0;
    return { cheaper, pricier: valid.length - cheaper, total: pos.length, avg };
  }, [pos]);

  const rows = useMemo(() => {
    const qq = query.trim();
    let list = pos.filter((p) => {
      const cheaper = (p.positioning_pct ?? 0) < 0;
      if (filter === "cheaper" && !cheaper) return false;
      if (filter === "pricier" && cheaper) return false;
      if (qq && !p.category_name.includes(qq)) return false;
      return true;
    });
    const dir = sort.dir === "asc" ? 1 : -1;
    list = [...list].sort((a, b) => {
      let c = 0;
      if (sort.key === "name") c = a.category_name.localeCompare(b.category_name, "ko");
      else if (sort.key === "cuckoo") c = a.own_avg_price - b.own_avg_price;
      else if (sort.key === "market") c = a.category_avg_price - b.category_avg_price;
      else if (sort.key === "models") c = a.own_product_count - b.own_product_count;
      else c = (a.positioning_pct ?? 0) - (b.positioning_pct ?? 0);
      return c * dir;
    });
    return list;
  }, [pos, query, filter, sort]);

  const cards = [
    { label: "시장보다 저렴", val: summary.cheaper + "개", sub: "쿠쿠 평균이 더 낮은 카테고리", color: C.down },
    { label: "시장보다 비쌈", val: summary.pricier + "개", sub: "쿠쿠 평균이 더 높은 카테고리", color: C.up },
    {
      label: "평균 가격 포지셔닝",
      val: (summary.avg > 0 ? "+" : "") + summary.avg.toFixed(2) + "%",
      sub: "시장 평균 대비",
      color: summary.avg < 0 ? C.down : C.up,
    },
    { label: "분석 카테고리", val: summary.total + "개", sub: "렌탈·부품 제외", color: C.ink },
  ];

  return (
    <div className="space-y-[18px]">
      {/* 요약 카드 */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3.5">
        {cards.map((c) => (
          <div key={c.label} className="bg-white border border-[#e9e9ee] rounded-[14px] px-[18px] py-4">
            <div className="text-xs text-[#8e8e99] font-semibold">{c.label}</div>
            <div className="text-[26px] font-extrabold tracking-[-0.02em] mt-1.5 tabular-nums" style={{ color: c.color }}>
              {c.val}
            </div>
            <div className="text-[11px] text-[#aaaab2] mt-0.5">{c.sub}</div>
          </div>
        ))}
      </div>

      {/* 포지셔닝 표 */}
      <div className="bg-white border border-[#e9e9ee] rounded-[14px] overflow-hidden">
        <div className="px-[18px] pt-4 pb-3.5 border-b border-[#f0f0f3]">
          <div className="flex items-center justify-between gap-3 flex-wrap">
            <div>
              <div className="text-[15px] font-bold">쿠쿠 가격 포지셔닝</div>
              <div className="text-xs text-[#9a9aa2] mt-0.5">
                카테고리별 쿠쿠 평균가 vs 시장 평균가 · 렌탈·부품 제외 · 모델 단위 집계
              </div>
            </div>
            <div className="flex items-center gap-2.5">
              <div className="flex items-center gap-1.5 bg-[#f1f1f4] border border-[#e6e6ec] rounded-lg px-2.5 py-1.5">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#9a9aa2" strokeWidth="2.2">
                  <circle cx="11" cy="11" r="7" />
                  <path d="m21 21-4.3-4.3" />
                </svg>
                <input
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="카테고리 검색"
                  className="bg-transparent outline-none w-[120px] text-[13px]"
                />
              </div>
              <div className="flex gap-1.5">
                {(["all", "cheaper", "pricier"] as const).map((k) => (
                  <button
                    key={k}
                    onClick={() => setFilter(k)}
                    className={`px-3 py-1.5 rounded-lg text-[13px] font-semibold ${
                      filter === k ? "bg-ink text-white" : "bg-[#f0f0f3] text-[#6b6b73]"
                    }`}
                  >
                    {k === "all" ? "전체" : k === "cheaper" ? "저렴" : "비쌈"}
                  </button>
                ))}
              </div>
            </div>
          </div>
          <div className="flex items-center gap-4 mt-3 text-[11px] text-[#8e8e99] flex-wrap">
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-[3px]" style={{ background: C.down }} />
              시장보다 저렴
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-[3px]" style={{ background: C.up }} />
              시장보다 비쌈
            </span>
            <span className="text-[#c8c8d0]">·</span>
            <span>막대 = 시장 평균 대비 가격 차이 (중앙 = 동일)</span>
          </div>
        </div>

        <div className="grid grid-cols-[1.3fr_1fr_1fr_2.2fr_0.7fr_0.9fr] gap-2.5 px-[18px] py-2.5 text-[11px] font-semibold text-[#9a9aa2] border-b border-[#f0f0f3] bg-[#fafafb]">
          <button onClick={() => clickSort("name")} className="text-left hover:text-[#6b6b73]">카테고리{arr("name")}</button>
          <button onClick={() => clickSort("cuckoo")} className="text-right hover:text-[#6b6b73]">쿠쿠 평균{arr("cuckoo")}</button>
          <button onClick={() => clickSort("market")} className="text-right hover:text-[#6b6b73]">시장 평균{arr("market")}</button>
          <button onClick={() => clickSort("pos")} className="text-center hover:text-[#6b6b73]">가격 포지셔닝{arr("pos")}</button>
          <div className="text-center">추세</div>
          <button onClick={() => clickSort("models")} className="text-right hover:text-[#6b6b73]">모델수{arr("models")}</button>
        </div>

        <div className="max-h-[620px] overflow-y-auto">
          {rows.map((p) => {
            const pp = p.positioning_pct ?? 0;
            const cheaper = pp < 0;
            const color = cheaper ? C.down : C.up;
            const mag = Math.min(Math.abs(pp), 100);
            return (
              <div
                key={p.category_id}
                onClick={() => onPick(p.category_id)}
                className="grid grid-cols-[1.3fr_1fr_1fr_2.2fr_0.7fr_0.9fr] gap-2.5 px-[18px] py-2.5 items-center border-b border-[#f4f4f6] cursor-pointer hover:bg-[#f8f8fb]"
              >
                <div className="text-[13px] font-semibold truncate">{p.category_name}</div>
                <div className="text-right text-[13px] font-bold tabular-nums">{won(p.own_avg_price)}</div>
                <div className="text-right text-[13px] text-[#595964] tabular-nums">{won(p.category_avg_price)}</div>
                <div className="flex items-center gap-2.5">
                  <div className="flex-1 flex items-center h-[22px]">
                    <div className="flex-1 flex justify-end items-center h-[9px]">
                      <div className="h-[9px] rounded-l-[4px]" style={{ background: C.down, width: `${cheaper ? mag : 0}%` }} />
                    </div>
                    <div className="w-px h-[18px] bg-[#d6d6dd]" />
                    <div className="flex-1 flex justify-start items-center h-[9px]">
                      <div className="h-[9px] rounded-r-[4px]" style={{ background: C.up, width: `${cheaper ? 0 : mag}%` }} />
                    </div>
                  </div>
                  <div className="w-[110px] flex items-center justify-end gap-1.5 shrink-0">
                    <span className="text-[13px] font-bold tabular-nums" style={{ color }}>
                      {(pp > 0 ? "+" : "") + pp.toFixed(2) + "%"}
                    </span>
                    <span
                      className="text-[10px] font-bold px-1.5 py-0.5 rounded-[5px]"
                      style={{ color, background: cheaper ? C.downTint : C.upTint }}
                    >
                      {cheaper ? "저렴" : "비쌈"}
                    </span>
                  </div>
                </div>
                <div className="flex justify-center">
                  <Spark vals={synthTrend(pp, 14, p.category_id)} color={color} w={70} h={22} />
                </div>
                <div className="text-right text-[13px] text-[#595964] tabular-nums">{p.own_product_count}</div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
