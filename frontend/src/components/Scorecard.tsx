import { useEffect, useState } from "react";
import { api, type Scorecard as SC } from "../api";
import { won } from "../format";

// ③ 모델 경쟁 스코어카드 — 선택 제품의 동급 시장 포지션(가격 순위·중앙값 대비·인접 경쟁)
export default function Scorecard({ productId }: { productId: number | null }) {
  const [sc, setSc] = useState<SC | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!productId) {
      setSc(null);
      return;
    }
    setLoading(true);
    api
      .scorecard(productId)
      .then(setSc)
      .catch(() => setSc(null))
      .finally(() => setLoading(false));
  }, [productId]);

  if (!productId) return null;
  if (loading) return <div className="rounded-xl bg-white border border-slate-100 p-4 text-xs text-slate-400">경쟁 분석 중…</div>;
  if (!sc) return null;

  const t = sc.target;
  const gap = sc.vs_median_pct;
  const gapColor = gap > 0 ? "text-rose-600" : gap < 0 ? "text-emerald-600" : "text-slate-500";

  return (
    <div className="rounded-xl bg-white border border-slate-100 shadow-sm p-4">
      <div className="flex items-center gap-2 mb-1">
        {t.is_own_brand && (
          <span className="text-[10px] bg-own/10 text-own px-1 py-0.5 rounded">쿠쿠</span>
        )}
        <span className="text-sm font-semibold text-slate-700 truncate">{t.model_name}</span>
      </div>
      <div className="text-[11px] text-slate-400 mb-3">동급 비교: {sc.tier}</div>

      {/* 핵심 지표 */}
      <div className="grid grid-cols-3 gap-2 mb-3">
        <div className="rounded-lg bg-slate-50 p-2 text-center">
          <div className="text-[11px] text-slate-400">가격 순위</div>
          <div className="text-base font-bold text-slate-700">
            {sc.rank}
            <span className="text-xs font-normal text-slate-400">/{sc.peer_count}</span>
          </div>
          <div className="text-[10px] text-slate-400">싼 순</div>
        </div>
        <div className="rounded-lg bg-slate-50 p-2 text-center">
          <div className="text-[11px] text-slate-400">현재가</div>
          <div className="text-sm font-bold text-slate-700">{won(t.current_price)}</div>
        </div>
        <div className="rounded-lg bg-slate-50 p-2 text-center">
          <div className="text-[11px] text-slate-400">중앙값 대비</div>
          <div className={`text-base font-bold ${gapColor}`}>
            {gap > 0 ? "+" : ""}
            {gap}%
          </div>
          <div className="text-[10px] text-slate-400">{won(sc.median)}</div>
        </div>
      </div>

      <div className="text-[11px] text-slate-500 mb-3">
        동급 {sc.peer_count}개 · 쿠쿠 {sc.own_count} · 경쟁 {sc.rival_count} · 더 싼 모델 {sc.cheaper}개 · 더 비싼 모델 {sc.pricier}개
      </div>

      {/* 인접 경쟁 모델 */}
      {sc.nearest.length > 0 && (
        <div>
          <div className="text-[11px] font-semibold text-slate-500 mb-1">가격 인접 경쟁 모델</div>
          <div className="space-y-1">
            {sc.nearest.map((n) => {
              const diff = n.current_price - t.current_price;
              return (
                <div key={n.product_id} className="flex items-center justify-between text-xs">
                  <span className="flex items-center gap-1 min-w-0">
                    {n.is_own_brand && (
                      <span className="shrink-0 text-[9px] bg-own/10 text-own px-1 rounded">쿠쿠</span>
                    )}
                    <span className="text-slate-400 shrink-0">{n.brand}</span>
                    <span className="truncate text-slate-600">{n.model_name}</span>
                  </span>
                  <span className="shrink-0 ml-2 tabular-nums">
                    {won(n.current_price)}
                    <span className={`ml-1 ${diff > 0 ? "text-rose-500" : "text-emerald-600"}`}>
                      ({diff > 0 ? "+" : ""}
                      {won(diff)})
                    </span>
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
