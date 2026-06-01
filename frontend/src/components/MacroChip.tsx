import { useEffect, useState } from "react";
import { api, type Macro } from "../api";

// 거시지표 칩(F12) — USD/KRW 최근값 + 90일 추세 방향
export default function MacroChip() {
  const [m, setM] = useState<Macro | null>(null);

  useEffect(() => {
    api.macro().then(setM).catch(() => setM(null));
  }, []);

  if (!m || m.latest == null || m.series.length < 2) return null;
  const first = m.series[0].value;
  const up = m.latest >= first;

  return (
    <span className="hidden sm:inline-flex items-center gap-1 text-xs text-slate-500 bg-slate-100 rounded-lg px-2.5 py-1">
      USD/KRW
      <span className="font-semibold text-slate-700">{m.latest.toLocaleString()}</span>
      <span className={up ? "text-up" : "text-down"}>{up ? "▲" : "▼"}</span>
      {m.is_synthetic && <span className="text-[9px] text-amber-500" title="데모 합성 데이터">데모</span>}
    </span>
  );
}
