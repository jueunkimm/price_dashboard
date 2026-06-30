import { useEffect, useMemo, useState } from "react";
import { api, type AlertItem, type MarketEvent } from "../../api";
import { pct } from "../../format";
import { C } from "./util";

// 디자인 핸드오프 — 알림·이벤트 탭: 변동 알림(좌) + 시장 이벤트 캘린더(우)
const KIND: Record<string, { label: string; bg: string; color: string }> = {
  season: { label: "시즌", bg: "#eef0fb", color: "#5b57d6" },
  sale: { label: "세일", bg: "#fdeee9", color: "#bf6a3a" },
  launch: { label: "출시", bg: "#e9f0f8", color: "#3a6aa8" },
};

export default function AlertsTab({ ownOnly, today }: { ownOnly: boolean; today: string }) {
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [events, setEvents] = useState<MarketEvent[]>([]);
  const [filter, setFilter] = useState<"all" | "up" | "down" | "cuckoo">("all");

  useEffect(() => {
    api.alerts(ownOnly, 100).then(setAlerts).catch(() => setAlerts([]));
  }, [ownOnly]);
  useEffect(() => {
    api.events().then(setEvents).catch(() => setEvents([]));
  }, []);

  const shown = useMemo(
    () =>
      alerts.filter((a) => {
        const up = (a.change_pct ?? 0) >= 0;
        if (filter === "up") return up;
        if (filter === "down") return !up;
        if (filter === "cuckoo") return a.is_own_brand;
        return true;
      }),
    [alerts, filter]
  );

  const now = new Date(today).getTime();
  const y0 = new Date("2026-01-01").getTime();
  const span = new Date("2026-12-31").getTime() - y0;
  const nowPct = ((now - y0) / span) * 100;

  return (
    <div className="grid grid-cols-1 lg:grid-cols-[1.25fr_1fr] gap-[18px] items-start">
      {/* 변동 알림 */}
      <div className="bg-white border border-[#e9e9ee] rounded-[14px] overflow-hidden">
        <div className="px-[18px] pt-4 pb-3.5 border-b border-[#f0f0f3]">
          <div className="flex items-center justify-between mb-3">
            <div className="text-[15px] font-bold">변동 알림</div>
            <span className="text-xs text-[#9a9aa2]">최근 24시간 · 인앱</span>
          </div>
          <div className="flex gap-1.5">
            {(["all", "up", "down", "cuckoo"] as const).map((k) => (
              <button
                key={k}
                onClick={() => setFilter(k)}
                className={`px-3 py-1.5 rounded-lg text-[13px] font-semibold ${
                  filter === k ? "bg-ink text-white" : "bg-[#f0f0f3] text-[#6b6b73]"
                }`}
              >
                {k === "all" ? "전체" : k === "up" ? "상승" : k === "down" ? "하락" : "쿠쿠"}
              </button>
            ))}
          </div>
        </div>
        {shown.length === 0 ? (
          <div className="py-12 text-center text-sm text-[#aaaab2]">표시할 알림이 없습니다.</div>
        ) : (
          <div>
            {shown.map((a) => {
              const up = (a.change_pct ?? 0) >= 0;
              const color = up ? C.up : C.down;
              const barW = (Math.min(Math.abs(a.change_pct ?? 0), 75) / 75) * 100;
              return (
                <div key={a.id} className="flex items-center gap-3.5 px-[18px] py-3.5 border-b border-[#f4f4f6] hover:bg-[#f8f8fb]">
                  <div className="w-[78px] shrink-0">
                    <div className="text-[14px] font-extrabold text-right tabular-nums" style={{ color }}>
                      {pct(a.change_pct)}
                    </div>
                    <div className="h-1 rounded-[2px] bg-[#f0f0f3] mt-1.5 overflow-hidden">
                      <div className="h-full float-right" style={{ background: color, width: `${barW}%` }} />
                    </div>
                  </div>
                  <div className="flex-1 min-w-0 flex items-center gap-1.5">
                    {a.is_own_brand && (
                      <span className="text-[10px] font-bold text-[#4b47c4] bg-[#ecebfb] px-1.5 py-0.5 rounded-[5px] shrink-0">
                        쿠쿠
                      </span>
                    )}
                    <span className="text-[13px] font-medium text-[#2c2c34] truncate">{a.title}</span>
                  </div>
                </div>
              );
            })}
          </div>
        )}
        <div className="px-[18px] py-3 text-[11px] text-[#aaaab2] bg-[#fafafb]">
          ※ 이메일·슬랙 발송은 자격증명·동의 설정 후 활성화 (현재 인앱 알림만)
        </div>
      </div>

      {/* 시장 이벤트 */}
      <div className="bg-white border border-[#e9e9ee] rounded-[14px] overflow-hidden">
        <div className="px-[18px] pt-4 pb-3.5 border-b border-[#f0f0f3]">
          <div className="text-[15px] font-bold">시장 이벤트</div>
          <div className="text-xs text-[#9a9aa2] mt-0.5">프로모션 · 시즌 캘린더 (2026)</div>
          <div className="relative h-6 mt-3.5">
            <div className="absolute top-[11px] left-0 right-0 h-0.5 bg-[#ededf1] rounded-[2px]" />
            <div className="absolute top-1.5 w-0.5 h-3 bg-ink rounded-[2px]" style={{ left: `${nowPct}%` }} />
            <div className="absolute -top-[3px] text-[10px] text-[#6b6b73] font-semibold -translate-x-1/2" style={{ left: `${nowPct}%` }}>
              오늘
            </div>
            <div className="absolute -bottom-[3px] left-0 text-[10px] text-[#bcbcc4]">1월</div>
            <div className="absolute -bottom-[3px] right-0 text-[10px] text-[#bcbcc4]">12월</div>
          </div>
        </div>
        <div className="py-1.5">
          {events.map((e) => {
            const k = KIND[e.event_type] ?? { label: e.event_type, bg: "#f0f0f3", color: "#9a9aa2" };
            const start = new Date(e.start_date).getTime();
            const end = e.end_date ? new Date(e.end_date).getTime() : start;
            const active = now >= start && now <= end;
            const upcoming = start > now;
            const status = active ? "진행중" : upcoming ? "예정" : "지남";
            const prog = active && end > start ? Math.min(100, Math.max(0, ((now - start) / (end - start)) * 100)) : 0;
            return (
              <div key={e.id} className="flex gap-3 px-[18px] py-3.5 border-b border-[#f4f4f6]">
                <div className="shrink-0 pt-0.5">
                  <span className="text-[11px] font-bold px-2 py-[3px] rounded-md" style={{ background: k.bg, color: k.color }}>
                    {k.label}
                  </span>
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-[14px] font-bold">{e.title}</span>
                    <span
                      className="text-[10px] font-bold px-[7px] py-0.5 rounded-[5px]"
                      style={{
                        background: active ? "#e4f3ea" : "#f0f0f3",
                        color: active ? "#2f8f5e" : "#9a9aa2",
                      }}
                    >
                      {status}
                    </span>
                  </div>
                  <div className="text-xs text-[#8e8e99] mt-1">
                    {e.start_date}
                    {e.end_date ? ` ~ ${e.end_date}` : ""}
                    {e.note ? ` · ${e.note}` : ""}
                  </div>
                  {active && (
                    <div className="flex items-center gap-2 mt-2">
                      <div className="flex-1 h-[5px] rounded-[3px] bg-[#eaf3ee] overflow-hidden">
                        <div className="h-full bg-[#2f8f5e]" style={{ width: `${prog}%` }} />
                      </div>
                      <span className="text-[11px] font-bold text-[#2f8f5e]">진행 {prog.toFixed(0)}%</span>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
