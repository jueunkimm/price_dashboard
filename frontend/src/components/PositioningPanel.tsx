import { useEffect, useState } from "react";
import { api, type Positioning, type SegPositioning, type SegProduct } from "../api";
import { won, pct, changeColor } from "../format";

// 쿠쿠 가격 포지셔닝(F-C): 카테고리별 쿠쿠 평균가 vs 카테고리 평균가 ±%
export default function PositioningPanel() {
  const [rows, setRows] = useState<Positioning[]>([]);
  const [seg, setSeg] = useState<SegPositioning[]>([]);
  const [mode, setMode] = useState<"category" | "segment">("category");
  const [openRow, setOpenRow] = useState<number | null>(null);

  useEffect(() => {
    api.positioning().then(setRows).catch(() => setRows([]));
    api.positioningSegmented().then(setSeg).catch(() => setSeg([]));
  }, []);

  if (!rows.length) return null;

  return (
    <div className="rounded-xl bg-white shadow-sm border border-slate-100 overflow-hidden">
      <div className="px-4 py-2 bg-own/5 border-b border-slate-100 flex items-center justify-between">
        <span className="text-sm font-semibold text-own">★ 쿠쿠 포지셔닝 (렌탈·부품 제외)</span>
        <div className="flex gap-1 text-xs">
          <button
            onClick={() => setMode("category")}
            className={`px-2 py-0.5 rounded ${mode === "category" ? "bg-own text-white" : "text-slate-500"}`}
          >
            카테고리 평균
          </button>
          <button
            onClick={() => setMode("segment")}
            className={`px-2 py-0.5 rounded ${mode === "segment" ? "bg-own text-white" : "text-slate-500"}`}
          >
            동급(용량) 비교
          </button>
        </div>
      </div>
      <div className="overflow-x-auto">
        {mode === "category" ? (
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-slate-500 text-xs">
              <tr>
                <th className="text-left px-3 py-2">카테고리</th>
                <th className="text-right px-3 py-2">쿠쿠 평균</th>
                <th className="text-right px-3 py-2">시장 평균</th>
                <th className="text-right px-3 py-2">포지셔닝</th>
                <th className="text-right px-3 py-2">모델수</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.category_id} className="border-t border-slate-50">
                  <td className="px-3 py-2">{r.category_name}</td>
                  <td className="px-3 py-2 text-right">{won(r.own_avg_price)}</td>
                  <td className="px-3 py-2 text-right text-slate-500">{won(r.category_avg_price)}</td>
                  <td className={`px-3 py-2 text-right font-medium ${changeColor(r.positioning_pct)}`}>
                    {pct(r.positioning_pct)}
                    <span className="text-[10px] text-slate-400 ml-1">
                      {r.positioning_pct != null && r.positioning_pct < 0 ? "저렴" : "비쌈"}
                    </span>
                  </td>
                  <td className="px-3 py-2 text-right text-slate-500">{r.own_product_count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : seg.length === 0 ? (
          <div className="px-4 py-6 text-center text-sm text-slate-400">
            동급 비교 가능한 용량 데이터가 부족합니다(제목에 용량 표기 없는 경우 많음).
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-slate-500 text-xs">
              <tr>
                <th className="text-left px-3 py-2">카테고리 · 용량</th>
                <th className="text-right px-3 py-2">쿠쿠 평균</th>
                <th className="text-right px-3 py-2">동급 평균</th>
                <th className="text-right px-3 py-2">포지셔닝</th>
                <th className="text-right px-3 py-2">표본</th>
              </tr>
            </thead>
            <tbody>
              {seg.map((s, i) => (
                <FragmentRow
                  key={i}
                  s={s}
                  open={openRow === i}
                  onToggle={() => setOpenRow(openRow === i ? null : i)}
                />
              ))}
            </tbody>
          </table>
        )}
      </div>
      {mode === "segment" && (
        <div className="px-4 py-1.5 text-[11px] text-slate-400 border-t border-slate-50">
          ※ 행을 클릭하면 비교된 제품이 보입니다. 동급은 제목·모델코드에서 추출된 용량 기준 — 표본 적은 구간은 참고만.
        </div>
      )}
    </div>
  );
}

// 동급 포지셔닝 한 행(클릭 시 비교된 제품 펼침)
function FragmentRow({
  s,
  open,
  onToggle,
}: {
  s: SegPositioning;
  open: boolean;
  onToggle: () => void;
}) {
  const ProductList = ({ title, items, accent }: { title: string; items: SegProduct[]; accent: string }) => (
    <div className="min-w-0">
      <div className={`text-xs font-semibold mb-1 ${accent}`}>
        {title} ({items.length})
      </div>
      {items.length === 0 ? (
        <div className="text-[11px] text-slate-400">없음</div>
      ) : (
        <ul className="space-y-0.5">
          {items.map((p, i) => (
            <li key={i} className="flex items-center justify-between gap-2 text-[12px]">
              <span className="truncate text-slate-600">
                <span className="text-slate-400">{p.brand}</span> {p.model_name}
              </span>
              <span className="shrink-0 text-slate-500">{won(p.current_price)}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );

  return (
    <>
      <tr
        onClick={onToggle}
        className="border-t border-slate-50 hover:bg-slate-50 cursor-pointer"
      >
        <td className="px-3 py-2">
          <span className="text-slate-400 mr-1">{open ? "▾" : "▸"}</span>
          {s.category_name} <span className="text-slate-400">· {s.capacity_band}</span>
        </td>
        <td className="px-3 py-2 text-right">{won(s.own_avg_price)}</td>
        <td className="px-3 py-2 text-right text-slate-500">{won(s.segment_avg_price)}</td>
        <td className={`px-3 py-2 text-right font-medium ${changeColor(s.positioning_pct)}`}>
          {pct(s.positioning_pct)}
        </td>
        <td className="px-3 py-2 text-right text-[11px] text-slate-400">
          쿠쿠 {s.own_product_count}/동급 {s.segment_size}
        </td>
      </tr>
      {open && (
        <tr className="bg-slate-50/60">
          <td colSpan={5} className="px-4 py-3">
            <div className="grid sm:grid-cols-2 gap-4">
              <ProductList title="★ 쿠쿠 모델" items={s.own_products} accent="text-own" />
              <ProductList title="동급 경쟁 모델" items={s.rival_products} accent="text-slate-600" />
            </div>
          </td>
        </tr>
      )}
    </>
  );
}
