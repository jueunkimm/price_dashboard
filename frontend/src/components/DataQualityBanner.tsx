import { useEffect, useState } from "react";
import { api, type DataQuality } from "../api";

// 데이터 신뢰성 배너(QA A-1/A-2) — 실측 vs 합성/데모 상태를 투명하게 고지
export default function DataQualityBanner() {
  const [dq, setDq] = useState<DataQuality | null>(null);

  useEffect(() => {
    api.dataQuality().then(setDq).catch(() => setDq(null));
  }, []);

  if (!dq) return null;

  const demoFlags: string[] = [];
  if (dq.has_synthetic_price) demoFlags.push("변동률·추세·알림(합성 전일가)");
  if (dq.demand_is_synthetic) demoFlags.push("수요");
  if (dq.macro_is_synthetic) demoFlags.push("환율");

  const allReal = !dq.has_synthetic_price && !dq.demand_is_synthetic && !dq.macro_is_synthetic;

  return (
    <div
      className={`rounded-lg border p-3 text-sm ${
        allReal
          ? "bg-emerald-50 border-emerald-200 text-emerald-700"
          : "bg-amber-50 border-amber-200 text-amber-800"
      }`}
    >
      {allReal ? (
        <div className="space-y-0.5">
          <span>✓ 전 지표 실측 데이터 (합성 0) · 실수집 {dq.real_collection_days}일 누적</span>
          {!dq.variation_ready && (
            <div className="text-xs text-emerald-600">
              변동률·추세·랭킹·알림은 <b>실수집 2일째부터</b> 표시됩니다 (현재 {dq.real_collection_days}일 — 월·금 수집 누적 중).
              가격·브랜드비교·수요·환율은 지금도 실데이터입니다.
            </div>
          )}
          <div className="text-[11px] text-emerald-600">
            정제: 부품 {dq.excluded_accessories}개·렌탈 {dq.excluded_rentals}개를 비교 풀에서 제외 / 모델 단위 dedup 적용
          </div>
        </div>
      ) : (
        <div className="space-y-0.5">
          <div className="font-medium">
            ⚠ 데모 데이터 포함 — 의사결정 인용 주의
          </div>
          <div className="text-xs">
            가격(표시가)은 <b>실측</b>(실수집 {dq.real_collection_days}일).
            {demoFlags.length > 0 && <> 다음은 <b>합성/데모</b>: {demoFlags.join(", ")}.</>}
            {!dq.variation_ready && " 변동률은 실수집 2일 이상 누적 시 실데이터화됩니다."}
          </div>
          <div className="text-[11px] text-amber-600">
            정제: 부품 {dq.excluded_accessories}개·렌탈 {dq.excluded_rentals}개를 비교 풀에서 제외 / 모델 단위 dedup 적용
          </div>
        </div>
      )}
    </div>
  );
}
