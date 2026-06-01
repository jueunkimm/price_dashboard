import { useEffect, useState } from "react";
import { api, type AlertItem } from "../api";
import { changeColor } from "../format";

// 변동 알림(F11) — 임계치 초과 변동을 인앱 알림으로 표시
export default function AlertsPanel({ ownOnly }: { ownOnly: boolean }) {
  const [alerts, setAlerts] = useState<AlertItem[]>([]);

  useEffect(() => {
    api.alerts(ownOnly, 20).then(setAlerts).catch(() => setAlerts([]));
  }, [ownOnly]);

  return (
    <div className="rounded-xl bg-white shadow-sm border border-slate-100 overflow-hidden">
      <div className="px-4 py-2 border-b border-slate-100 text-sm font-semibold text-slate-600 flex items-center justify-between">
        <span>변동 알림</span>
        <span className="text-xs font-normal text-slate-400">{alerts.length}건 · 인앱</span>
      </div>
      {alerts.length === 0 ? (
        <div className="px-4 py-6 text-center text-sm text-slate-400">알림 없음</div>
      ) : (
        <ul className="divide-y divide-slate-50 max-h-72 overflow-y-auto">
          {alerts.map((a) => (
            <li key={a.id} className="px-4 py-2 flex items-center gap-2 text-sm">
              {a.is_own_brand && (
                <span className="text-[10px] bg-own/10 text-own px-1.5 py-0.5 rounded shrink-0">
                  쿠쿠
                </span>
              )}
              <span className={`shrink-0 font-medium ${changeColor(a.change_pct)}`}>
                {a.change_pct != null ? `${a.change_pct > 0 ? "+" : ""}${a.change_pct.toFixed(1)}%` : ""}
              </span>
              <span className="truncate text-slate-600">{a.title.replace(/^\[[^\]]+\]\s*[▲▼]\S+\s*·\s*/, "")}</span>
            </li>
          ))}
        </ul>
      )}
      <div className="px-4 py-1.5 text-[11px] text-slate-400 border-t border-slate-50">
        ※ 이메일/슬랙 발송은 자격증명·동의 설정 후 활성화(현재 인앱 알림만)
      </div>
    </div>
  );
}
