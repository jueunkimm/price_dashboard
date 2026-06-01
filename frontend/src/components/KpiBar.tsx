import type { Kpi } from "../api";
import { pct, won, changeColor } from "../format";

function Card({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="rounded-xl bg-white p-4 shadow-sm border border-slate-100">
      <div className="text-xs text-slate-500 mb-1">{label}</div>
      <div className="text-lg font-semibold">{children}</div>
    </div>
  );
}

export default function KpiBar({ kpi, ownOnly }: { kpi: Kpi | null; ownOnly: boolean }) {
  if (!kpi) return null;
  return (
    <div className="grid grid-cols-2 xl:grid-cols-4 gap-3">
      <Card label={ownOnly ? "쿠쿠 제품 수" : "트래킹 제품 수"}>
        {kpi.product_count.toLocaleString()}
      </Card>
      <Card label="평균 변동률">
        <span className={changeColor(kpi.avg_change_pct)}>{pct(kpi.avg_change_pct)}</span>
      </Card>
      <Card label="급변 제품 수">
        <span className={kpi.anomaly_count > 0 ? "text-up" : ""}>{kpi.anomaly_count}</span>
      </Card>
      {ownOnly ? (
        <Card label="쿠쿠 평균 포지셔닝(평균 대비)">
          <span className={changeColor(kpi.own_avg_positioning_pct)}>
            {pct(kpi.own_avg_positioning_pct)}
          </span>
        </Card>
      ) : (
        <Card label="최대 등락">
          <div className="flex flex-col gap-0.5 text-sm">
            <span className="text-up truncate" title={kpi.top_up?.model_name}>
              ▲ {kpi.top_up ? pct(kpi.top_up.change_pct) : "-"}
              {kpi.top_up && <span className="text-slate-400"> · {won(kpi.top_up.current_price)}</span>}
            </span>
            <span className="text-down truncate" title={kpi.top_down?.model_name}>
              ▼ {kpi.top_down ? pct(kpi.top_down.change_pct) : "-"}
              {kpi.top_down && <span className="text-slate-400"> · {won(kpi.top_down.current_price)}</span>}
            </span>
          </div>
        </Card>
      )}
    </div>
  );
}
