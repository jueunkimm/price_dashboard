import { useMemo, useState } from "react";
import { type CategoryOverview } from "../../api";
import { won } from "../../format";
import { C, synthTrend } from "./util";
import Spark from "./Spark";

// 디자인 핸드오프 — 카테고리별 시장 현황(시장 평균가·모델수·급변·추세). 행 클릭 → 드릴다운.
type SortKey = "name" | "market" | "models" | "surge";

export default function CategoryTable({
  cats,
  q,
  onPick,
}: {
  cats: CategoryOverview[];
  q: string;
  onPick: (categoryId: number) => void;
}) {
  const [group, setGroup] = useState<"all" | "kitchen">("all");
  const [sort, setSort] = useState<{ key: SortKey; dir: "asc" | "desc" }>({ key: "surge", dir: "desc" });

  const clickSort = (key: SortKey) =>
    setSort((s) =>
      s.key === key ? { key, dir: s.dir === "asc" ? "desc" : "asc" } : { key, dir: key === "name" ? "asc" : "desc" }
    );
  const arrow = (key: SortKey) => (sort.key === key ? (sort.dir === "asc" ? " ▲" : " ▼") : "");

  const rows = useMemo(() => {
    const qq = q.trim();
    let list = cats.filter((c) => {
      if (group === "kitchen" && !(c.group || "").includes("주방")) return false;
      if (qq && !c.category_name.includes(qq)) return false;
      return true;
    });
    const dir = sort.dir === "asc" ? 1 : -1;
    list = [...list].sort((a, b) => {
      let cmp = 0;
      if (sort.key === "name") cmp = a.category_name.localeCompare(b.category_name, "ko");
      else if (sort.key === "market") cmp = a.avg_price - b.avg_price;
      else if (sort.key === "models") cmp = a.product_count - b.product_count;
      else cmp = a.anomaly_count - b.anomaly_count;
      return cmp * dir;
    });
    return list;
  }, [cats, group, q, sort]);

  return (
    <div className="bg-white border border-[#e9e9ee] rounded-[14px] overflow-hidden">
      <div className="px-[18px] pt-4 pb-3 border-b border-[#f0f0f3] flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-baseline gap-2">
          <span className="text-[15px] font-bold">카테고리별 시장 현황</span>
          <span className="text-xs text-[#9a9aa2]">시장 평균가 · 등록 모델 · 급변 · 클릭 시 상세</span>
        </div>
        <div className="flex gap-1.5">
          {(["all", "kitchen"] as const).map((k) => (
            <button
              key={k}
              onClick={() => setGroup(k)}
              className={`px-3 py-1.5 rounded-lg text-[13px] font-semibold ${
                group === k ? "bg-ink text-white" : "bg-[#f0f0f3] text-[#6b6b73]"
              }`}
            >
              {k === "all" ? "전체" : "주방가전"}
            </button>
          ))}
        </div>
      </div>
      <div className="grid grid-cols-[1.4fr_1fr_0.8fr_0.8fr_1fr] gap-2 px-[18px] py-2.5 text-[11px] font-semibold text-[#9a9aa2] border-b border-[#f0f0f3]">
        <button onClick={() => clickSort("name")} className="text-left hover:text-[#6b6b73]">
          카테고리{arrow("name")}
        </button>
        <button onClick={() => clickSort("market")} className="text-right hover:text-[#6b6b73]">
          시장 평균가{arrow("market")}
        </button>
        <button onClick={() => clickSort("models")} className="text-right hover:text-[#6b6b73]">
          모델수{arrow("models")}
        </button>
        <button onClick={() => clickSort("surge")} className="text-right hover:text-[#6b6b73]">
          급변{arrow("surge")}
        </button>
        <div className="text-right">30일 추세</div>
      </div>
      <div className="max-h-[560px] overflow-y-auto">
        {rows.map((c) => (
          <div
            key={c.category_id}
            onClick={() => onPick(c.category_id)}
            className="grid grid-cols-[1.4fr_1fr_0.8fr_0.8fr_1fr] gap-2 px-[18px] py-3 items-center border-b border-[#f4f4f6] cursor-pointer hover:bg-[#f8f8fb]"
          >
            <div className="text-[13px] font-semibold truncate">
              {c.has_own_lineup && <span className="text-own mr-0.5">★</span>}
              {c.category_name}
            </div>
            <div className="text-right text-[13px] font-bold tabular-nums">{won(c.avg_price)}</div>
            <div className="text-right text-[13px] text-[#595964] tabular-nums">{c.product_count}</div>
            <div className="text-right">
              {c.anomaly_count > 0 && (
                <span className="text-[11px] font-bold text-up bg-[#fbecea] px-2 py-0.5 rounded-md">
                  급변 {c.anomaly_count}
                </span>
              )}
            </div>
            <div className="flex justify-end">
              <Spark vals={synthTrend(c.median_change_pct ?? 0, 14, c.category_id)} color={C.neutralSpark} w={84} h={26} />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
