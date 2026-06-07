import { useEffect, useState } from "react";
import { api, type QAReport } from "../api";

// 자동 데이터 품질 점검(QA) — 매 수집마다 생성되는 qa_report.json을 노출.
// 수기 점검을 대체: 시드 후보 브랜드 / 신규 카테고리 후보 / 오배치를 자동 탐지.
export default function QAPanel() {
  const [qa, setQa] = useState<QAReport | null>(null);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    api.qaReport().then(setQa).catch(() => setQa(null));
  }, []);

  if (!qa) return null;
  const m = qa.metrics;

  return (
    <div className="rounded-xl bg-white border border-slate-100 shadow-sm">
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between gap-3 px-4 py-2.5"
      >
        <span className="flex items-center gap-2 min-w-0 flex-wrap">
          <span className="text-sm font-semibold text-slate-600 shrink-0">🩺 데이터 품질 점검(자동)</span>
          <span className="text-[11px] text-slate-400">
            기타/미상 {m.unknown_brand_pct}% · 오배치 {m.offcategory} · 시드후보 {m.brand_candidates} · 신규카테고리후보 {m.category_candidates}
          </span>
        </span>
        <span className="text-xs text-slate-400 shrink-0">{open ? "접기 ▴" : "펼치기 ▾"}</span>
      </button>

      {open && (
        <div className="border-t border-slate-100 px-4 py-3 grid md:grid-cols-3 gap-4 text-xs">
          {/* ① 시드 후보 브랜드 */}
          <div>
            <div className="font-semibold text-slate-600 mb-1">시드 추가 후보 브랜드</div>
            <div className="text-[11px] text-slate-400 mb-2">기타/미상 중 브랜드로 보이는 빈출명 (시드하면 매칭 회복)</div>
            <div className="space-y-1 max-h-56 overflow-auto">
              {qa.brand_candidates.length === 0 && <div className="text-slate-400">없음</div>}
              {qa.brand_candidates.map((b) => (
                <div key={b.brand} className="flex items-center justify-between gap-2">
                  <span className="truncate">
                    <b className="text-slate-700">{b.brand}</b>
                    <span className="text-slate-400"> · {b.categories.join(", ")}</span>
                  </span>
                  <span className="shrink-0 text-slate-500 tabular-nums">{b.count}건</span>
                </div>
              ))}
            </div>
          </div>

          {/* ② 신규 카테고리 후보 */}
          <div>
            <div className="font-semibold text-slate-600 mb-1">신규 카테고리 후보</div>
            <div className="text-[11px] text-slate-400 mb-2">네이버 분류에 제품이 많은데 추적 안 하는 품목군</div>
            <div className="space-y-1.5 max-h-56 overflow-auto">
              {qa.category_candidates.length === 0 && <div className="text-slate-400">없음</div>}
              {qa.category_candidates.map((c) => (
                <div key={c.naver_cat}>
                  <div className="flex items-center justify-between gap-2">
                    <b className="text-slate-700 truncate">{c.naver_cat}</b>
                    <span className="shrink-0 text-slate-500 tabular-nums">{c.count}개</span>
                  </div>
                  <div className="text-[10px] text-slate-400 truncate">{c.samples.join(" · ")}</div>
                </div>
              ))}
            </div>
          </div>

          {/* ③ 오배치 */}
          <div>
            <div className="font-semibold text-slate-600 mb-1">오배치(가격 통계 제외됨)</div>
            <div className="text-[11px] text-slate-400 mb-2">네이버 분류가 카테고리와 달라 평균을 흐리던 제품</div>
            <div className="space-y-1 max-h-56 overflow-auto">
              {qa.offcategory.length === 0 && <div className="text-slate-400">없음</div>}
              {qa.offcategory.map((o, i) => (
                <div key={i} className="flex items-center justify-between gap-2">
                  <span className="truncate">
                    <b className="text-slate-700">{o.category}</b>
                    <span className="text-orange-500"> ⟵ {o.naver_cat || "미분류"}</span>
                  </span>
                  <span className="shrink-0 text-slate-500 tabular-nums">{o.count}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
