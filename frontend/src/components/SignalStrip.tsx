import type { CategoryOverview } from "../api";
import { won, pct, changeColor, arrow } from "../format";

// 카테고리 상세 상단 '신호 요약' — 핵심 지표(중앙값·변동·범위·급변)를 한 줄로.
// 흩어진 숫자를 위로 모아 한눈에 읽히게 한다(가격 신호 가독성).
function Tile({ label, children, hint }: { label: string; children: React.ReactNode; hint?: string }) {
  return (
    <div className="rounded-lg bg-white border border-slate-100 px-3 py-2 min-w-0">
      <div className="text-[10px] text-slate-400 mb-0.5 truncate">{label}</div>
      <div className="text-sm font-bold tabular-nums truncate">{children}</div>
      {hint && <div className="text-[10px] text-slate-400 truncate">{hint}</div>}
    </div>
  );
}

export default function SignalStrip({ cat }: { cat: CategoryOverview }) {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
      <Tile label="중앙값 가격" hint={`평균 ${won(cat.avg_price)}`}>
        {won(cat.median_price)}
      </Tile>
      <Tile label="중앙값 변동(직전 수집 대비)">
        <span className={changeColor(cat.median_change_pct)}>
          {arrow(cat.median_change_pct)} {pct(cat.median_change_pct)}
        </span>
      </Tile>
      <Tile label="가격 범위" hint={`${cat.product_count}개 모델`}>
        <span className="text-xs">
          {won(cat.min_price)} ~ {won(cat.max_price)}
        </span>
      </Tile>
      <Tile label="급변 모델">
        <span className={cat.anomaly_count > 0 ? "text-up" : "text-slate-400"}>
          {cat.anomaly_count}건
        </span>
      </Tile>
    </div>
  );
}
