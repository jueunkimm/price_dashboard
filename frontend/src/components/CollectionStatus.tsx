import { useEffect, useState } from "react";
import { api, type CollectionLog } from "../api";

export default function CollectionStatus() {
  const [log, setLog] = useState<CollectionLog | null>(null);

  useEffect(() => {
    api.collectionLogs(1).then((rows) => setLog(rows[0] ?? null)).catch(() => {});
  }, []);

  if (!log) return null;
  const when = log.finished_at ?? log.started_at;
  const dt = when ? new Date(when).toLocaleString("ko-KR") : "-";
  const ok = log.status === "success";

  return (
    <div className="flex items-center gap-2 text-xs text-slate-400">
      <span
        className={`inline-block w-2 h-2 rounded-full ${ok ? "bg-emerald-500" : "bg-amber-500"}`}
      />
      <span>
        최근 수집 {dt} · {log.categories_done}개 카테고리 · {log.snapshots_inserted.toLocaleString()}건
        {!ok && ` · ${log.status}`}
      </span>
    </div>
  );
}
