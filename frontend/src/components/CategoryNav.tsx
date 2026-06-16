import { useMemo, useState } from "react";
import type { CategoryOverview } from "../api";
import { won, pct, changeColor, arrow } from "../format";

// 대분류 표시 순서(시드 CATEGORY_TREE 기준). 미정의 그룹은 뒤로.
const GROUP_ORDER = ["주방가전", "생활가전", "계절·환경가전", "영상·음향가전", "미용·건강가전"];

function CategoryCard({
  c,
  selected,
  onClick,
}: {
  c: CategoryOverview;
  selected: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={`text-left rounded-xl bg-white p-3 shadow-sm border transition hover:shadow-md ${
        selected ? "border-own ring-1 ring-own" : "border-slate-100"
      }`}
    >
      <div className="flex items-center justify-between gap-1 mb-1">
        <span className="font-semibold text-sm truncate">
          {c.has_own_lineup && <span className="text-own mr-0.5">★</span>}
          {c.category_name}
        </span>
        <span className="text-[10px] text-slate-400 shrink-0">{c.product_count}</span>
      </div>
      <div className="text-base font-bold tabular-nums">{won(c.median_price)}</div>
      <div className="flex items-center justify-between gap-1 mt-0.5">
        <span className={`text-xs font-medium ${changeColor(c.median_change_pct)}`}>
          {arrow(c.median_change_pct)} {pct(c.median_change_pct)}
        </span>
        {c.anomaly_count > 0 && (
          <span className="text-[10px] bg-up/10 text-up px-1 py-0.5 rounded shrink-0">
            급변 {c.anomaly_count}
          </span>
        )}
      </div>
    </button>
  );
}

// 그룹(대분류)별로 묶고 이름 검색이 되는 카테고리 탐색.
export default function CategoryNav({
  cats,
  selectedId,
  onSelect,
}: {
  cats: CategoryOverview[];
  selectedId: number | null;
  onSelect: (c: CategoryOverview | null) => void;
}) {
  const [q, setQ] = useState("");
  const [ownOnly, setOwnOnly] = useState(false);

  const groups = useMemo(() => {
    const t = q.trim();
    const filtered = cats.filter(
      (c) => (!t || c.category_name.includes(t)) && (!ownOnly || c.has_own_lineup)
    );
    const m = new Map<string, CategoryOverview[]>();
    for (const c of filtered) {
      const g = c.group || "기타";
      (m.get(g) ?? m.set(g, []).get(g)!).push(c);
    }
    for (const list of m.values())
      list.sort(
        (a, b) =>
          Number(b.has_own_lineup) - Number(a.has_own_lineup) ||
          a.category_name.localeCompare(b.category_name, "ko")
      );
    return [...m.entries()].sort((a, b) => {
      const ia = GROUP_ORDER.indexOf(a[0]);
      const ib = GROUP_ORDER.indexOf(b[0]);
      return (ia < 0 ? 99 : ia) - (ib < 0 ? 99 : ib);
    });
  }, [cats, q, ownOnly]);

  const total = groups.reduce((n, [, l]) => n + l.length, 0);

  if (!cats.length)
    return (
      <div className="text-slate-400 text-sm py-8 text-center">
        데이터가 없습니다. 수집을 먼저 실행하세요 (collector.collect).
      </div>
    );

  return (
    <div className="space-y-4">
      {/* 검색 + ★ 토글 */}
      <div className="flex items-center gap-2 flex-wrap">
        <div className="relative flex-1 min-w-[180px]">
          <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-300 text-sm">🔎</span>
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="카테고리 검색 (예: 세탁기, 정수기)"
            className="w-full text-sm border border-slate-200 rounded-lg pl-8 pr-3 py-2"
          />
        </div>
        <button
          onClick={() => setOwnOnly((v) => !v)}
          className={`px-3 py-2 rounded-lg text-xs font-medium transition shrink-0 ${
            ownOnly ? "bg-own text-white" : "bg-slate-100 text-slate-500"
          }`}
        >
          ★ 쿠쿠 라인업만
        </button>
        <span className="text-xs text-slate-400 shrink-0">{total}개</span>
      </div>

      {total === 0 && (
        <div className="text-slate-400 text-sm py-6 text-center">검색 결과가 없습니다.</div>
      )}

      {groups.map(([g, list]) => (
        <div key={g}>
          <div className="flex items-center gap-2 mb-2">
            <h3 className="text-xs font-semibold text-slate-500">{g}</h3>
            <span className="text-[10px] text-slate-300">{list.length}</span>
            <div className="flex-1 h-px bg-slate-100" />
          </div>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-2.5">
            {list.map((c) => (
              <CategoryCard
                key={c.category_id}
                c={c}
                selected={selectedId === c.category_id}
                onClick={() => onSelect(selectedId === c.category_id ? null : c)}
              />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
