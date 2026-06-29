import { useEffect, useMemo, useState } from "react";
import { api, type FilteredProduct, type ProductFilters } from "../api";
import { won, pct, changeColor } from "../format";
import { downloadCsv, csvBtnClass } from "../csv";

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
  const [showOff, setShowOff] = useState(false); // 타분류 추정(off_category) 표시 여부
  const [showAcc, setShowAcc] = useState(false); // 별매품(부품·소모품) 표시 여부

  // 기본은 오배치/별매품을 숨겨 본품 비교 신뢰도를 높이고, 토글로 투명하게 확인 가능.
  const offCount = useMemo(
    () => rows.filter((r) => r.off_category && !r.is_accessory).length,
    [rows]
  );
  const accCount = useMemo(() => rows.filter((r) => r.is_accessory).length, [rows]);
  const visible = useMemo(
    () =>
      rows.filter(
        (r) => (showOff || !r.off_category) && (showAcc || !r.is_accessory)
      ),
    [rows, showOff, showAcc]
  );

  // 컬럼 정렬(헤더 클릭 → 오름/내림 토글). 용량은 밴드의 첫 숫자로 정렬.
  type SortKey = "name" | "cap" | "price" | "chg";
  const [sort, setSort] = useState<{ key: SortKey; dir: "asc" | "desc" } | null>(null);
  const clickSort = (key: SortKey) =>
    setSort((s) =>
      s?.key === key
        ? { key, dir: s.dir === "asc" ? "desc" : "asc" }
        : { key, dir: key === "name" ? "asc" : "desc" }
    );
  const sorted = useMemo(() => {
    if (!sort) return visible;
    const capNum = (b: string | null) => {
      const m = (b || "").match(/\d+(?:\.\d+)?/);
      return m ? parseFloat(m[0]) : -1;
    };
    const dir = sort.dir === "asc" ? 1 : -1;
    return [...visible].sort((a, b) => {
      let c = 0;
      if (sort.key === "name") c = a.model_name.localeCompare(b.model_name, "ko");
      else if (sort.key === "cap") c = capNum(a.capacity_band) - capNum(b.capacity_band);
      else if (sort.key === "price") c = a.current_price - b.current_price;
      else c = (a.change_pct ?? -Infinity) - (b.change_pct ?? -Infinity);
      return c * dir;
    });
  }, [visible, sort]);

  // 현재 필터 결과의 가격 요약(평균·중앙값·최저·최고).
  // '전체' 모드에서 일시불가와 렌탈 월요금이 섞이면 평균이 왜곡되므로,
  // 렌탈 모드일 때만 월요금 기준으로 계산하고 그 외엔 일시불(비렌탈)만 집계.
  const stat = useMemo(() => {
    // 오배치(off_category) 제품은 가격 평균을 흐리므로 통계에서 제외
    const base = (filters.pricing === "rental" ? rows : rows.filter((r) => !r.is_rental)).filter(
      (r) => !r.off_category && !r.is_accessory
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
      <div className="flex items-center justify-between gap-2 px-3 py-1.5 border-b border-slate-50">
        <span className="flex items-center gap-2 min-w-0">
          <span className="text-xs text-slate-400 shrink-0">{loading ? "조회 중…" : `${visible.length}건`}</span>
          {offCount > 0 && (
            <button
              onClick={() => setShowOff((v) => !v)}
              className="text-[11px] text-orange-500 hover:underline shrink-0"
              title="네이버 분류가 이 카테고리와 달라 오배치로 추정되는 제품"
            >
              {showOff ? `타분류 추정 ${offCount}건 숨기기` : `타분류 추정 ${offCount}건 보기`}
            </button>
          )}
          {accCount > 0 && (
            <button
              onClick={() => setShowAcc((v) => !v)}
              className="text-[11px] text-violet-500 hover:underline shrink-0"
              title="부품·소모품(별매품) — 본품 비교·가격 통계에서 제외됨"
            >
              {showAcc ? `별매품 ${accCount}건 숨기기` : `별매품 ${accCount}건 보기`}
            </button>
          )}
        </span>
        {visible.length > 0 && (
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
                sorted
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

      {visible.length === 0 ? (
        <div className="py-12 text-center text-slate-400 text-sm">
          {loading
            ? "불러오는 중…"
            : offCount > 0 || accCount > 0
            ? "표시할 본품이 없습니다(타분류·별매품 제외). 위 ‘보기’로 확인하세요."
            : "조건에 맞는 제품이 없습니다."}
        </div>
      ) : (
        <div className="max-h-[60vh] overflow-auto rounded-b-xl">
        <table className="w-full text-sm table-fixed">
          <thead className="bg-slate-50 text-slate-500 text-xs sticky top-0 z-10">
            <tr>
              {([
                { k: "name", label: "제품", align: "text-left", w: "" },
                { k: "cap", label: "용량", align: "text-left", w: "w-16" },
                { k: "price", label: "현재가", align: "text-right", w: "w-28" },
                { k: "chg", label: "변동", align: "text-right", w: "w-16" },
              ] as const).map((col) => (
                <th
                  key={col.k}
                  onClick={() => clickSort(col.k)}
                  className={`${col.align} ${col.w} px-3 py-2 cursor-pointer select-none hover:text-slate-700`}
                >
                  {col.label}
                  <span className="text-own ml-0.5">
                    {sort?.key === col.k ? (sort.dir === "asc" ? "▲" : "▼") : ""}
                  </span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sorted.map((r) => (
              <tr
                key={r.product_id}
                onClick={() => onSelect(r.product_id)}
                className="border-t border-slate-50 hover:bg-slate-50 cursor-pointer align-top"
              >
                <td className="px-3 py-2 overflow-hidden">
                  <div className="min-w-0">
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
                        {r.is_accessory && (
                          <span className="shrink-0 text-[10px] bg-violet-100 text-violet-600 px-1 py-0.5 rounded" title="별매품(부품·소모품) — 본품 비교·가격 통계에서 제외됨">별매품</span>
                        )}
                        {/* 링크 있으면 상품 페이지(↗), 없으면 네이버 쇼핑 검색으로 폴백(모두 클릭 가능) */}
                        <a
                          href={
                            r.link ||
                            `https://search.shopping.naver.com/search/all?query=${encodeURIComponent(r.model_name)}`
                          }
                          target="_blank"
                          rel="noopener noreferrer"
                          onClick={(e) => e.stopPropagation()}
                          title={r.link ? "네이버 상품 페이지 열기" : "네이버 쇼핑에서 검색"}
                          className="truncate hover:text-own hover:underline decoration-own/40"
                        >
                          {r.model_name}
                        </a>
                        <a
                          href={
                            r.link ||
                            `https://search.shopping.naver.com/search/all?query=${encodeURIComponent(r.model_name)}`
                          }
                          target="_blank"
                          rel="noopener noreferrer"
                          onClick={(e) => e.stopPropagation()}
                          title={r.link ? "네이버 상품 페이지 열기" : "네이버 쇼핑에서 검색"}
                          className="shrink-0 text-slate-300 hover:text-own"
                        >
                          {r.link ? "↗" : "⌕"}
                        </a>
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
