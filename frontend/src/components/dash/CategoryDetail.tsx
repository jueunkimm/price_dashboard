import { useState } from "react";
import { type CategoryOverview, type ProductFilters } from "../../api";
import SignalStrip from "../SignalStrip";
import BrandComparePanel from "../BrandComparePanel";
import ProductResults from "../ProductResults";
import TrendChart from "../TrendChart";
import Scorecard from "../Scorecard";
import DemandPanel from "../DemandPanel";

// 드릴다운 — 카테고리 클릭 시 제품 목록·스코어카드·가격추세·수요(기존 컴포넌트 재사용)
export default function CategoryDetail({
  cat,
  filters,
  ownOnly,
  onPatchFilters,
  onClear,
}: {
  cat: CategoryOverview;
  filters: ProductFilters;
  ownOnly: boolean;
  onPatchFilters: (patch: Partial<ProductFilters>) => void;
  onClear: () => void;
}) {
  const [selectedProduct, setSelectedProduct] = useState<number | null>(null);

  return (
    <div className="space-y-[18px]">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <h2 className="text-[15px] font-bold text-ink">
          {cat.has_own_lineup ? "★ " : ""}
          {cat.category_name}
          {filters.capacity_band && <span className="text-own ml-1">· {filters.capacity_band}</span>}
        </h2>
        <button onClick={onClear} className="text-xs text-own hover:underline">
          ← 전체 시장 현황으로
        </button>
      </div>

      <SignalStrip cat={cat} />

      <BrandComparePanel categoryId={cat.category_id} categoryName={cat.category_name} filters={filters} />

      <div className="grid lg:grid-cols-5 gap-[18px]">
        <section className="lg:col-span-3 min-w-0">
          <h3 className="text-sm font-semibold text-[#595964] mb-2">제품 목록</h3>
          <ProductResults filters={filters} ownOnly={ownOnly} onSelect={setSelectedProduct} />
        </section>
        <section className="lg:col-span-2 min-w-0 space-y-4">
          <div>
            <h3 className="text-sm font-semibold text-[#595964] mb-2">가격 추세</h3>
            <TrendChart productId={selectedProduct} />
          </div>
          {selectedProduct && (
            <div>
              <h3 className="text-sm font-semibold text-[#595964] mb-2">동급 경쟁 스코어카드</h3>
              <Scorecard productId={selectedProduct} />
            </div>
          )}
          <DemandPanel
            categoryId={cat.category_id}
            categoryName={cat.category_name}
            priceChange={cat.median_change_pct}
          />
        </section>
      </div>

      {/* 용량/세부 필터 잔여 표시 — 초기화 */}
      {(filters.capacity_band || filters.brand_id || filters.sub_category) && (
        <button
          onClick={() => onPatchFilters({ capacity_band: undefined, brand_id: undefined, sub_category: undefined })}
          className="text-xs text-[#8e8e99] hover:text-ink hover:underline"
        >
          용량·브랜드 필터 초기화
        </button>
      )}
    </div>
  );
}
