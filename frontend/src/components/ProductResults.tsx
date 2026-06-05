import { useEffect, useMemo, useState } from "react";
import { api, type FilteredProduct, type ProductFilters } from "../api";
import { won, pct, changeColor } from "../format";
import { downloadCsv, csvBtnClass } from "../csv";

// 네이버 쇼핑 CDN은 핫링크를 차단하므로 무료 이미지 프록시(weserv.nl)로 우회 + 80px 리사이즈.
function thumb(url: string): string {
  return `https://images.weserv.nl/?url=${encodeURIComponent(url.replace(/^https?:\/\//, ""))}&w=80&h=80&fit=cover`;
}

// 필터된 제품 결과 테이블 — 사이드바 필터 + 헤더 쿠쿠 토글 반영
export default function ProductResults({
  filters,
  ownOnly,
  onSelect,
}: {
  filters: ProductFilters;
  ownOnly: boolean;
  onSelect: (productId: number) => void;
}) {
  const [rows, setRows] = useState<FilteredProduct[]>([]);
  const [loading, setLoading] = useState(false);

  // 현재 필터 결과의 가격 요약(평균·중앙값·최저·최고).
  // '전체' 모드에서 일시불가와 렌탈 월요금이 섞이면 평균이 왜곡되므로,
  // 렌탈 모드일 때만 월요금 기준으로 계산하고 그 외엔 일시불(비렌탈)만 집계.
  const stat = useMemo(() => {
    // 오배치(off_category) 제품은 가격 평균을 흐리므로 통계에서 제외
    const base = (filters.pricing === "rental" ? rows : rows.filter((r) => !r.is_rental)).filter(
      (r) => !r.off_category
    );
    const prices = base.map((r) => r.current_price).sort((a, b) => a - b);
    if (!prices.length) return null;
    const sum = prices.reduce((a, b) => a + b, 0);
    const mid = Math.floor(prices.length / 2);
    const median = prices.length % 2 ? prices[mid] : (prices[mid - 1] + prices[mid]) / 2;
    return {
      count: prices.length,
      avg: Math.round(sum / prices.length),
      median: Math.round(median),
      min: prices[0],
      max: prices[prices.length - 1],
    };
  }, [rows, filters.pricing]);

  useEffect(() => {
    setLoading(true);
    // 브랜드를 명시적으로 고르면 그 선택이 "쿠쿠만 보기" 토글보다 우선(충돌 방지).
    const ownEffective = (ownOnly || !!filters.own_only) && !filters.brand_id;
    api
      .productSearch({ ...filters, own_only: ownEffective })
      .then(setRows)
      .catch(() => setRows([]))
      .finally(() => setLoading(false));
  }, [filters, ownOnly]);

  return (
    <div className="rounded-xl bg-white border border-slate-100 shadow-sm">
      <div className="flex items-center justify-between px-3 py-1.5 border-b border-slate-50">
        <span className="text-xs text-slate-400">{loading ? "조회 중…" : `${rows.length}건`}</span>
        {rows.length > 0 && (
          <button
            onClick={() =>
              downloadCsv(
                "제품목록.csv",
                [
                  { key: "model_name", label: "모델명" },
                  { key: "brand", label: "브랜드" },
                  { key: "category_name", label: "카테고리" },
                  { key: "sub_category", label: "세부유형" },
                  { key: "capacity_band", label: "용량" },
                  { key: "mall", label: "판매몰" },
                  { key: "current_price", label: "현재가" },
                  { key: "change_pct", label: "변동률(%)" },
                ],
                rows
              )
            }
            className={csvBtnClass}
          >
            ⬇ CSV
          </button>
        )}
      </div>

      {stat && (
        <div className="flex flex-wrap items-center gap-x-5 gap-y-1 px-3 py-2 bg-slate-50/70 border-b border-slate-100 text-sm">
          {filters.capacity_band && (
            <span className="text-xs font-semibold text-own">{filters.capacity_band}</span>
          )}
          {filters.pricing === "rental" && (
            <span className="text-[11px] font-semibold text-amber-700 bg-amber-100 px-1.5 py-0.5 rounded">
              렌탈 · 월 요금 기준
            </span>
          )}
          <span className="text-slate-500">
            평균 <b className="text-slate-700">{won(stat.avg)}</b>
          </span>
          <span className="text-slate-500">
            중앙값 <b className="text-slate-700">{won(stat.median)}</b>
          </span>
          <span className="text-slate-400 text-xs">
            최저 {won(stat.min)} · 최고 {won(stat.max)} · {stat.count}개
          </span>
        </div>
      )}

      {rows.length === 0 ? (
        <div className="py-12 text-center text-slate-400 text-sm">
          {loading ? "불러오는 중…" : "조건에 맞는 제품이 없습니다."}
        </div>
      ) : (
        <div className="max-h-[60vh] overflow-auto rounded-b-xl">
        <table className="w-full text-sm table-fixed">
          <thead className="bg-slate-50 text-slate-500 text-xs sticky top-0 z-10">
            <tr>
              <th className="text-left px-3 py-2">제품</th>
              <th className="text-left px-3 py-2 w-16">용량</th>
              <th className="text-right px-3 py-2 w-28">현재가</th>
              <th className="text-right px-3 py-2 w-16">변동</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr
                key={r.product_id}
                onClick={() => onSelect(r.product_id)}
                className="border-t border-slate-50 hover:bg-slate-50 cursor-pointer align-top"
              >
                <td className="px-3 py-2 overflow-hidden">
                  <div className="flex items-center gap-2 min-w-0">
                    {/* 썸네일(네이버 핫링크) — 클릭 시 상품 페이지, 깨지면 회색 박스 */}
                    {r.link ? (
                      <a
                        href={r.link}
                        target="_blank"
                        rel="noopener noreferrer"
                        onClick={(e) => e.stopPropagation()}
                        title="네이버 상품 페이지 열기"
                        className="shrink-0 w-10 h-10 rounded bg-slate-100 overflow-hidden block"
                      >
                        {r.image_url && (
                          <img
                            src={thumb(r.image_url)}
                            alt=""
                            loading="lazy"
                            referrerPolicy="no-referrer"
                            className="w-full h-full object-cover"
                            onError={(e) => (e.currentTarget.style.display = "none")}
                          />
                        )}
                      </a>
                    ) : (
                      <div className="shrink-0 w-10 h-10 rounded bg-slate-100 overflow-hidden">
                        {r.image_url && (
                          <img
                            src={thumb(r.image_url)}
                            alt=""
                            loading="lazy"
                            referrerPolicy="no-referrer"
                            className="w-full h-full object-cover"
                            onError={(e) => (e.currentTarget.style.display = "none")}
                          />
                        )}
                      </div>
                    )}
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-1 min-w-0">
                        {r.is_own_brand && (
                          <span className="shrink-0 text-[10px] bg-own/10 text-own px-1 py-0.5 rounded">쿠쿠</span>
                        )}
                        {r.is_rental && (
                          <span className="shrink-0 text-[10px] bg-amber-100 text-amber-700 px-1 py-0.5 rounded">렌탈</span>
                        )}
                        {r.off_category && (
                          <span className="shrink-0 text-[10px] bg-orange-100 text-orange-600 px-1 py-0.5 rounded" title="네이버 분류가 이 카테고리와 달라 가격 통계에서 제외됨">타분류?</span>
                        )}
                        <span className="truncate">{r.model_name}</span>
                        {r.link && (
                          <a
                            href={r.link}
                            target="_blank"
                            rel="noopener noreferrer"
                            onClick={(e) => e.stopPropagation()}
                            title="네이버 상품 페이지 열기"
                            className="shrink-0 text-slate-300 hover:text-own"
                          >
                            ↗
                          </a>
                        )}
                      </div>
                      <div className="text-[11px] text-slate-400 truncate mt-0.5">
                        <span className="text-slate-500">{r.brand}</span>
                        {r.mall && (
                          <>
                            {" · "}
                            {r.mall === "쿠팡" ? (
                              <span className="text-rose-500 font-medium">쿠팡</span>
                            ) : (
                              r.mall
                            )}
                          </>
                        )}
                        {r.sub_category && <span className="text-slate-400">{" · "}{r.sub_category}</span>}
                      </div>
                    </div>
                  </div>
                </td>
                <td className="px-3 py-2 text-slate-500 whitespace-nowrap">{r.capacity_band ?? "—"}</td>
                <td className="px-3 py-2 text-right whitespace-nowrap tabular-nums">
                  {won(r.current_price)}
                  {r.is_rental && <span className="text-[10px] text-slate-400 ml-0.5">/월</span>}
                </td>
                <td className={`px-3 py-2 text-right whitespace-nowrap font-medium tabular-nums ${changeColor(r.change_pct)}`}>
                  {pct(r.change_pct)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        </div>
      )}
    </div>
  );
}
