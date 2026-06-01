import { useEffect, useState } from "react";
import { api, type WeeklyReport } from "../api";
import { pct, changeColor } from "../format";

// 주간 요약 리포트(F13)
export default function ReportPanel() {
  const [rep, setRep] = useState<WeeklyReport | null>(null);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    api.report().then(setRep).catch(() => setRep(null));
  }, []);

  if (!rep) return null;

  const Stat = ({ label, children }: { label: string; children: React.ReactNode }) => (
    <div className="text-center">
      <div className="text-[11px] text-slate-400">{label}</div>
      <div className="text-sm font-semibold">{children}</div>
    </div>
  );

  return (
    <div className="rounded-xl bg-white shadow-sm border border-slate-100 overflow-hidden">
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full px-4 py-2 border-b border-slate-100 text-sm font-semibold text-slate-600 flex items-center justify-between"
      >
        <span>
          주간 요약 리포트 <span className="text-xs font-normal text-slate-400">· {rep.generated_for} 기준</span>
        </span>
        <span className="text-xs text-slate-400">{open ? "접기 ▲" : "Top 변동 펼치기 ▼"}</span>
      </button>
      <div className="grid grid-cols-3 sm:grid-cols-6 gap-2 px-4 py-3">
        <Stat label="카테고리">{rep.category_count}</Stat>
        <Stat label="평균 변동">
          <span className={changeColor(rep.avg_category_change_pct)}>
            {pct(rep.avg_category_change_pct)}
          </span>
        </Stat>
        <Stat label="급변">{rep.total_anomalies}</Stat>
        <Stat label="쿠쿠 포지셔닝">
          <span className={changeColor(rep.own_avg_positioning_pct)}>
            {pct(rep.own_avg_positioning_pct)}
          </span>
        </Stat>
        <Stat label="USD/KRW">{rep.usd_krw ?? "-"}</Stat>
        <Stat label="오늘 알림">{rep.alerts_today}</Stat>
      </div>
      {open && (
        <ul className="divide-y divide-slate-50 border-t border-slate-100">
          {rep.top_movers.map((m, i) => (
            <li key={i} className="px-4 py-1.5 flex items-center gap-2 text-sm">
              {m.is_own_brand && (
                <span className="text-[10px] bg-own/10 text-own px-1.5 py-0.5 rounded shrink-0">
                  쿠쿠
                </span>
              )}
              <span className={`shrink-0 font-medium ${changeColor(m.change_pct)}`}>
                {pct(m.change_pct)}
              </span>
              <span className="text-slate-400 text-xs shrink-0">{m.category}</span>
              <span className="truncate text-slate-600">{m.model_name}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
