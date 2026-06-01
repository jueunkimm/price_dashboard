import { useEffect, useState } from "react";
import { api, type MarketEvent } from "../api";

const TYPE_STYLE: Record<string, string> = {
  sale: "bg-up/10 text-up",
  season: "bg-emerald-100 text-emerald-700",
  launch: "bg-down/10 text-down",
};
const TYPE_LABEL: Record<string, string> = {
  sale: "세일",
  season: "시즌",
  launch: "출시",
};

// 프로모션/시즌 캘린더(F10) — 변동 추세 해석 시 시즌 노이즈 분리용 참고
export default function EventsPanel({ today }: { today: string }) {
  const [events, setEvents] = useState<MarketEvent[]>([]);

  useEffect(() => {
    api.events().then(setEvents).catch(() => setEvents([]));
  }, []);

  if (!events.length) return null;
  const now = new Date(today);

  return (
    <div className="rounded-xl bg-white shadow-sm border border-slate-100 overflow-hidden">
      <div className="px-4 py-2 border-b border-slate-100 text-sm font-semibold text-slate-600">
        프로모션·시즌 캘린더
      </div>
      <ul className="divide-y divide-slate-50">
        {events.map((e) => {
          const start = new Date(e.start_date);
          const end = e.end_date ? new Date(e.end_date) : start;
          const active = now >= start && now <= end;
          const upcoming = start > now;
          return (
            <li key={e.id} className="px-4 py-2.5 flex items-center gap-3">
              <span
                className={`text-[10px] px-1.5 py-0.5 rounded shrink-0 ${
                  TYPE_STYLE[e.event_type] ?? "bg-slate-100 text-slate-500"
                }`}
              >
                {TYPE_LABEL[e.event_type] ?? e.event_type}
              </span>
              <div className="min-w-0 flex-1">
                <div className="text-sm font-medium truncate">
                  {e.title}
                  {active && (
                    <span className="ml-2 text-[10px] bg-emerald-500 text-white px-1.5 py-0.5 rounded">
                      진행중
                    </span>
                  )}
                </div>
                <div className="text-[11px] text-slate-400">
                  {e.start_date}
                  {e.end_date ? ` ~ ${e.end_date}` : ""} · {e.note}
                </div>
              </div>
              {upcoming && <span className="text-[11px] text-slate-400 shrink-0">예정</span>}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
