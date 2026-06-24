import type { RankingRow } from "../api";
import { won, pct, changeColor, arrow } from "../format";
import { downloadCsv, csvBtnClass } from "../csv";

export default function MovementTable({
  rows,
  onSelect,
}: {
  rows: RankingRow[];
  onSelect: (productId: number) => void;
}) {
  if (!rows.length)
    return <div className="text-slate-400 text-sm py-8 text-center">변동 데이터가 없습니다.</div>;

  const exportCsv = () =>
    downloadCsv(
      "변동랭킹.csv",
      [
        { key: "model_name", label: "모델명" },
        { key: "category_name", label: "카테고리" },
        { key: "current_price", label: "현재가" },
        { key: "prev_price", label: "전일가" },
        { key: "change_pct", label: "변동률(%)" },
        { key: "is_own_brand", label: "쿠쿠" },
        { key: "is_rental", label: "렌탈" },
      ],
      rows
    );

  return (
    <div className="rounded-xl bg-white shadow-sm border border-slate-100">
      <div className="flex items-center justify-between px-3 py-1.5 border-b border-slate-50">
        <span className="text-xs text-slate-400">{rows.length}건 · 스크롤로 더 보기</span>
        <button onClick={exportCsv} className={csvBtnClass}>⬇ CSV</button>
      </div>
      <div className="max-h-[28rem] overflow-auto rounded-b-xl">
      <table className="w-full text-sm">
        <thead className="bg-slate-50 text-slate-500 text-xs sticky top-0 z-10">
          <tr>
            <th className="text-left px-3 py-2">제품</th>
            <th className="text-left px-3 py-2">카테고리</th>
            <th className="text-right px-3 py-2">현재가</th>
            <th className="text-right px-3 py-2">변동률</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr
              key={r.product_id}
              onClick={() => onSelect(r.product_id)}
              className="border-t border-slate-50 hover:bg-slate-50 cursor-pointer"
            >
              <td className="px-3 py-2 max-w-xs truncate">
                {r.is_own_brand && (
                  <span className="text-[10px] bg-own/10 text-own px-1.5 py-0.5 rounded mr-1">
                    쿠쿠
                  </span>
                )}
                {r.is_rental && (
                  <span className="text-[10px] bg-amber-100 text-amber-700 px-1.5 py-0.5 rounded mr-1">
                    렌탈
                  </span>
                )}
                {r.model_name}
              </td>
              <td className="px-3 py-2 text-slate-500">{r.category_name}</td>
              <td className="px-3 py-2 text-right">{won(r.current_price)}</td>
              <td className={`px-3 py-2 text-right font-medium ${changeColor(r.change_pct)}`}>
                {arrow(r.change_pct)} {pct(r.change_pct)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      </div>
    </div>
  );
}
