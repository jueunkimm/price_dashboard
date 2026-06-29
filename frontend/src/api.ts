// 백엔드 API 클라이언트 (vite proxy 로 /api → :8000)

export interface CategoryOverview {
  category_id: number;
  category_name: string;
  group: string;
  has_own_lineup: boolean;
  product_count: number;
  avg_price: number;
  median_price: number;
  min_price: number;
  max_price: number;
  median_change_pct: number | null;
  anomaly_count: number;
}

export interface RankingRow {
  product_id: number;
  model_name: string;
  category_name: string;
  is_own_brand: boolean;
  is_rental: boolean;
  current_price: number;
  prev_price: number | null;
  change_pct: number;
  is_anomaly: boolean;
}

export interface Positioning {
  category_id: number;
  category_name: string;
  own_avg_price: number;
  category_avg_price: number;
  own_min_price: number;
  positioning_pct: number | null;
  own_product_count: number;
}

export interface MarketEvent {
  id: number;
  title: string;
  event_type: string;
  category_id: number | null;
  start_date: string;
  end_date: string | null;
  note: string | null;
}

export interface DemandPoint {
  date: string;
  ratio: number;
}
export interface Demand {
  category_id: number;
  is_synthetic: boolean;
  search: DemandPoint[];
  shopping: DemandPoint[];
}

export interface QAReport {
  metrics: {
    products: number;
    unknown_brand_pct: number;
    offcategory: number;
    brand_candidates: number;
    category_candidates: number;
  };
  brand_candidates: { brand: string; count: number; categories: string[] }[];
  category_candidates: { naver_cat: string; count: number; samples: string[] }[];
  offcategory: { category: string; naver_cat: string; count: number }[];
}

export interface DataQuality {
  real_collection_days: number;
  has_synthetic_price: boolean;
  synthetic_price_snapshots: number;
  demand_is_synthetic: boolean;
  macro_is_synthetic: boolean;
  total_products: number;
  excluded_accessories: number;
  excluded_rentals: number;
  variation_ready: boolean;
}

export interface SegProduct {
  model_name: string;
  brand: string;
  current_price: number;
}
export interface SegPositioning {
  category_id: number;
  category_name: string;
  capacity_band: string;
  own_avg_price: number;
  segment_avg_price: number;
  segment_size: number;
  own_product_count: number;
  positioning_pct: number | null;
  own_products: SegProduct[]; // 이 구간의 쿠쿠 모델
  rival_products: SegProduct[]; // 같은 구간의 경쟁(비자사) 모델
}

export interface BrandRow {
  brand: string;
  brand_id: number | null;
  is_own: boolean;
  model_count: number;
  avg_price: number;
  min_price: number;
  median_change_pct: number | null;
}

export interface AlertItem {
  id: number;
  title: string;
  change_pct: number | null;
  is_own_brand: boolean;
  period: string;
  dispatched: boolean;
  created_at: string;
}

export interface Macro {
  metric: string;
  latest: number | null;
  is_synthetic: boolean;
  series: { date: string; value: number }[];
}

export interface WeeklyReport {
  generated_for: string;
  category_count: number;
  avg_category_change_pct: number | null;
  total_anomalies: number;
  own_product_count: number;
  own_avg_positioning_pct: number | null;
  usd_krw: number | null;
  alerts_today: number;
  top_movers: {
    model_name: string;
    category: string;
    change_pct: number;
    is_own_brand: boolean;
  }[];
}

export interface CollectionLog {
  id: number;
  started_at: string;
  finished_at: string | null;
  status: string;
  categories_done: number;
  products_collected: number;
  snapshots_inserted: number;
  message: string | null;
}

export interface Kpi {
  avg_change_pct: number | null;
  anomaly_count: number;
  product_count: number;
  top_up: RankingRow | null;
  top_down: RankingRow | null;
  own_avg_positioning_pct?: number | null;
}

export interface TimeseriesPoint {
  date: string;
  price: number;
}
export interface Timeseries {
  product_id: number;
  model_name: string;
  is_own_brand: boolean;
  series: TimeseriesPoint[];
}

export interface ProductRow {
  product_id: number;
  model_name: string;
  category_id: number;
  brand_raw: string | null;
  is_own_brand: boolean;
  is_rental: boolean;
}

export interface FilterOptions {
  capacity_bands: string[];
  sub_categories: string[];
  brands: { id: number; name: string; is_own: boolean }[];
  malls: { name: string; count: number }[];
  price_min: number;
  price_max: number;
}

export interface ScoreItem {
  product_id: number;
  model_name: string;
  brand: string;
  is_own_brand: boolean;
  current_price: number;
}
export interface Scorecard {
  target: ScoreItem;
  tier: string; // 동급 정의(카테고리 · 용량 · 세부유형)
  peer_count: number;
  rank: number; // 1 = 최저가
  cheaper: number;
  pricier: number;
  median: number;
  vs_median_pct: number; // (타깃-중앙값)/중앙값*100
  own_count: number;
  rival_count: number;
  nearest: ScoreItem[]; // 가격이 가장 가까운 경쟁/동급 모델
}

export interface FilteredProduct {
  product_id: number;
  model_name: string;
  category_name: string;
  brand: string;
  capacity_band: string | null;
  sub_category: string | null;
  off_category: boolean;
  mall: string | null;
  image_url: string | null;
  link: string | null;
  is_own_brand: boolean;
  is_rental: boolean;
  is_accessory: boolean; // 별매품(부품·소모품) — 통계·비교 제외, 목록은 토글로 표시
  current_price: number;
  change_pct: number | null;
}

export interface ProductFilters {
  category_id?: number;
  brand_id?: number;
  capacity_band?: string;
  sub_category?: string;
  min_price?: number;
  max_price?: number;
  own_only?: boolean;
  exclude_rental?: boolean; // (구) 렌탈 제외 플래그 — pricing 미지정 시 호환용
  pricing?: "onetime" | "rental" | "all"; // 일시불(기본)·렌탈만·전체
  q?: string;
  mall?: string;
}

// 네이버 category4가 없는 상품을 담는 세부유형 버킷 라벨
export const UNCLASSIFIED = "미분류";

// ── 정적 JSON 데이터 레이어 (백엔드 없음 · GitHub Pages용) ──
// GitHub Actions가 하루 2회 생성한 /data/*.json 을 읽고, 파라미터형은 브라우저에서 필터링.
const BASE = import.meta.env.BASE_URL; // 예: '/' 또는 '/price-dashboard/'
const _cache = new Map<string, Promise<unknown>>();

function loadJSON<T>(name: string): Promise<T> {
  if (!_cache.has(name)) {
    _cache.set(
      name,
      fetch(`${BASE}data/${name}.json`).then((r) => {
        if (!r.ok) throw new Error(`data/${name}.json → ${r.status}`);
        return r.json();
      })
    );
  }
  return _cache.get(name)! as Promise<T>;
}

// products.json 한 행(필터 원본)
interface PRow extends FilteredProduct {
  category_id: number;
  brand_id: number | null;
  model_key: string | null;
  prev_price: number | null;
}

// 백엔드 _dedup_by_model 재현 — 같은 (카테고리,모델키)는 최저가 1건
function dedup(rows: PRow[]): PRow[] {
  const groups = new Map<string, PRow>();
  const out: PRow[] = [];
  for (const r of rows) {
    if (!r.model_key) {
      out.push(r);
      continue;
    }
    const k = `${r.category_id}:${r.model_key}`;
    const cur = groups.get(k);
    if (!cur || r.current_price < cur.current_price) groups.set(k, r);
  }
  return [...out, ...groups.values()];
}

function applyFilters(
  rows: PRow[],
  f: ProductFilters,
  ownOnly: boolean,
  includeAccessory = false
): PRow[] {
  // 일시불(기본)·렌탈만·전체. 구 exclude_rental 플래그도 계속 지원.
  const pricing = f.pricing ?? (f.exclude_rental === false ? "all" : "onetime");
  const filtered = rows.filter((p) => {
    // 별매품은 기본 제외(통계·검색 보호). 제품목록만 토글로 포함(includeAccessory).
    if (!includeAccessory && p.is_accessory) return false;
    if (pricing === "onetime" && p.is_rental) return false;
    if (pricing === "rental" && !p.is_rental) return false;
    if ((ownOnly || f.own_only) && !p.is_own_brand) return false;
    if (f.category_id && p.category_id !== f.category_id) return false;
    if (f.brand_id != null && p.brand_id !== f.brand_id) return false;
    if (f.capacity_band && p.capacity_band !== f.capacity_band) return false;
    if (f.sub_category) {
      // 네이버가 세부분류(category4)를 안 준 상품은 null → "미분류" 버킷으로 매칭(누락 방지)
      if (f.sub_category === UNCLASSIFIED) {
        if (p.sub_category) return false;
      } else if (p.sub_category !== f.sub_category) return false;
    }
    if (f.mall && (p.mall ?? "") !== f.mall) return false;
    if (f.min_price != null && p.current_price < f.min_price) return false;
    if (f.max_price != null && p.current_price > f.max_price) return false;
    if (f.q && !p.model_name.toLowerCase().includes(f.q.toLowerCase())) return false;
    return true;
  });
  return dedup(filtered);
}

export const api = {
  kpi: (ownOnly: boolean) => loadJSON<Kpi>(ownOnly ? "kpi_own" : "kpi_all"),
  categories: (ownOnly: boolean) =>
    loadJSON<CategoryOverview[]>(ownOnly ? "categories_own" : "categories_all"),
  ranking: (ownOnly: boolean, limit = 50) =>
    loadJSON<RankingRow[]>(ownOnly ? "ranking_own" : "ranking_all").then((r) => r.slice(0, limit)),
  timeseries: (productId: number) =>
    loadJSON<Record<string, Timeseries>>("timeseries").then(
      (m) => m[String(productId)] ?? { product_id: productId, model_name: "", is_own_brand: false, series: [] }
    ),
  // 전체 시계열 맵(비교 워크벤치: 스파크라인 + 다중 제품 정규화 비교)
  timeseriesAll: () => loadJSON<Record<string, Timeseries>>("timeseries"),
  positioning: () => loadJSON<Positioning[]>("positioning"),
  // 동급(용량) 포지셔닝 — products.json에서 브라우저 계산(어떤 제품끼리 비교했는지 포함)
  positioningSegmented: () =>
    loadJSON<PRow[]>("products").then((rows) => {
      const clean = dedup(rows.filter((p) => !p.is_rental && !p.is_accessory));
      const groups = new Map<string, PRow[]>();
      for (const p of clean) {
        if (!p.capacity_band) continue;
        const k = `${p.category_id}|${p.category_name}|${p.capacity_band}`;
        let list = groups.get(k);
        if (!list) {
          list = [];
          groups.set(k, list);
        }
        list.push(p);
      }
      const toSeg = (p: PRow): SegProduct => ({
        model_name: p.model_name,
        brand: p.brand,
        current_price: p.current_price,
      });
      const out: SegPositioning[] = [];
      for (const [k, list] of groups) {
        const own = list.filter((p) => p.is_own_brand);
        if (!own.length) continue;
        const [cidStr, cname, band] = k.split("|");
        const all = list.map((p) => p.current_price);
        const ownAvg = Math.round(own.reduce((a, p) => a + p.current_price, 0) / own.length);
        const segAvg = Math.round(all.reduce((a, b) => a + b, 0) / all.length);
        out.push({
          category_id: Number(cidStr),
          category_name: cname,
          capacity_band: band,
          own_avg_price: ownAvg,
          segment_avg_price: segAvg,
          segment_size: list.length,
          own_product_count: own.length,
          positioning_pct: segAvg ? Math.round(((ownAvg - segAvg) / segAvg) * 1000) / 10 : null,
          own_products: own.sort((a, b) => a.current_price - b.current_price).map(toSeg),
          rival_products: list
            .filter((p) => !p.is_own_brand)
            .sort((a, b) => a.current_price - b.current_price)
            .map(toSeg),
        });
      }
      out.sort((a, b) =>
        a.category_name === b.category_name
          ? a.capacity_band.localeCompare(b.capacity_band)
          : a.category_name.localeCompare(b.category_name)
      );
      return out;
    }),
  collectionLogs: (limit = 5) =>
    loadJSON<CollectionLog[]>("collection_logs").then((r) => r.slice(0, limit)),
  events: () => loadJSON<MarketEvent[]>("events"),
  demand: (categoryId: number) =>
    loadJSON<Record<string, Demand>>("demand").then(
      (m) => m[String(categoryId)] ?? { category_id: categoryId, is_synthetic: false, search: [], shopping: [] }
    ),
  alerts: (ownOnly: boolean, limit = 30) =>
    loadJSON<AlertItem[]>("alerts").then((r) =>
      (ownOnly ? r.filter((a) => a.is_own_brand) : r).slice(0, limit)
    ),
  macro: () => loadJSON<Macro>("macro"),
  report: () => loadJSON<WeeklyReport>("report"),
  dataQuality: () => loadJSON<DataQuality>("data_quality"),
  qaReport: () => loadJSON<QAReport>("qa_report"),

  // 파라미터형 — products.json에서 브라우저 필터링
  products: (q: string, ownOnly: boolean, limit = 20) =>
    loadJSON<PRow[]>("products").then((rows) =>
      applyFilters(rows, { q, exclude_rental: false }, ownOnly)
        .slice(0, limit)
        .map((p) => ({
          product_id: p.product_id,
          model_name: p.model_name,
          category_id: p.category_id,
          brand_raw: p.brand,
          is_own_brand: p.is_own_brand,
          is_rental: p.is_rental,
        }))
    ),

  productSearch: (f: ProductFilters) =>
    loadJSON<PRow[]>("products").then((rows) =>
      // 별매품 포함 반환(목록에서 배지+토글로 구분) — 통계는 컴포넌트에서 제외
      applyFilters(rows, f, !!f.own_only, true)
        .sort((a, b) => a.current_price - b.current_price)
        .slice(0, 200)
    ),

  // ③ 모델 경쟁 스코어카드 — 선택 제품의 동급(카테고리·용량·세부유형) 포지션
  scorecard: (productId: number) =>
    loadJSON<PRow[]>("products").then((rows): Scorecard | null => {
      const clean = rows.filter((p) => !p.is_rental && !p.off_category && !p.is_accessory);
      const dd = dedup(clean); // 모델 단위 최저가 대표
      const clicked = clean.find((p) => p.product_id === productId);
      if (!clicked) return null;
      const sameTier = (p: PRow) =>
        p.category_id === clicked.category_id &&
        (!clicked.capacity_band || p.capacity_band === clicked.capacity_band) &&
        (!clicked.sub_category || p.sub_category === clicked.sub_category);
      const peers = dd.filter(sameTier);
      const target =
        (clicked.model_key && peers.find((p) => p.model_key === clicked.model_key)) ||
        peers.find((p) => p.product_id === productId) ||
        clicked;
      const prices = peers.map((p) => p.current_price).sort((a, b) => a - b);
      const mid = Math.floor(prices.length / 2);
      const median = prices.length
        ? prices.length % 2
          ? prices[mid]
          : (prices[mid - 1] + prices[mid]) / 2
        : target.current_price;
      const cheaper = peers.filter((p) => p.current_price < target.current_price).length;
      const toItem = (p: PRow): ScoreItem => ({
        product_id: p.product_id,
        model_name: p.model_name,
        brand: p.brand,
        is_own_brand: p.is_own_brand,
        current_price: p.current_price,
      });
      const nearest = peers
        .filter((p) => (target.model_key ? p.model_key !== target.model_key : p.product_id !== target.product_id))
        .sort(
          (a, b) =>
            Math.abs(a.current_price - target.current_price) -
            Math.abs(b.current_price - target.current_price)
        )
        .slice(0, 5)
        .map(toItem);
      const tier = [
        clicked.category_name,
        clicked.capacity_band,
        clicked.sub_category,
      ]
        .filter(Boolean)
        .join(" · ");
      return {
        target: toItem(target),
        tier,
        peer_count: peers.length,
        rank: cheaper + 1,
        cheaper,
        pricier: peers.length - cheaper - 1,
        median: Math.round(median),
        vs_median_pct: median ? Math.round(((target.current_price - median) / median) * 1000) / 10 : 0,
        own_count: peers.filter((p) => p.is_own_brand).length,
        rival_count: peers.filter((p) => !p.is_own_brand).length,
        nearest,
      };
    }),

  filterOptions: (categoryId?: number) =>
    loadJSON<PRow[]>("products").then((rows) => {
      const inCat = categoryId ? rows.filter((p) => p.category_id === categoryId) : rows;
      const bands = [...new Set(inCat.map((p) => p.capacity_band).filter(Boolean))].sort() as string[];
      const subCatsReal = [...new Set(inCat.map((p) => p.sub_category).filter(Boolean))].sort() as string[];
      // 실제 세부유형이 하나라도 있고, 미분류(null) 상품도 있으면 "미분류" 옵션을 추가해 누락 방지
      const hasUnclassified = inCat.some((p) => !p.sub_category);
      const subCats =
        subCatsReal.length && hasUnclassified ? [...subCatsReal, UNCLASSIFIED] : subCatsReal;
      const brandMap = new Map<number, { id: number; name: string; is_own: boolean }>();
      for (const p of inCat) if (p.brand_id != null) brandMap.set(p.brand_id, { id: p.brand_id, name: p.brand, is_own: p.is_own_brand });
      const brands = [...brandMap.values()].sort((a, b) => (a.is_own === b.is_own ? a.name.localeCompare(b.name) : a.is_own ? -1 : 1));
      const mallCount = new Map<string, number>();
      for (const p of inCat) if (p.mall) mallCount.set(p.mall, (mallCount.get(p.mall) ?? 0) + 1);
      const malls = [...mallCount.entries()].sort((a, b) => b[1] - a[1]).map(([name, count]) => ({ name, count }));
      const prices = inCat.map((p) => p.current_price);
      return {
        capacity_bands: bands,
        sub_categories: subCats,
        brands,
        malls,
        price_min: prices.length ? Math.min(...prices) : 0,
        price_max: prices.length ? Math.max(...prices) : 0,
      } as FilterOptions;
    }),

  brandComparison: (categoryId: number, f: ProductFilters = {}) =>
    loadJSON<PRow[]>("products").then((rows) => {
      // own_only/brand는 비교 위해 미적용, 용량·몰·가격·렌탈 필터는 제품 목록과 동일.
      // 오배치(off_category)는 가격 비교를 흐리므로 제외(가스오븐레인지에 섞인 전기제품 등).
      const items = applyFilters(rows.filter((p) => p.category_id === categoryId && !p.off_category), {
        capacity_band: f.capacity_band,
        sub_category: f.sub_category,
        mall: f.mall,
        min_price: f.min_price,
        max_price: f.max_price,
        exclude_rental: f.exclude_rental,
        pricing: f.pricing,
      }, false);
      const byBrand = new Map<string, PRow[]>();
      for (const r of items) {
        const label = r.brand_id != null ? r.brand : "기타/미상";
        let list = byBrand.get(label);
        if (!list) {
          list = [];
          byBrand.set(label, list);
        }
        list.push(r);
      }
      const out: BrandRow[] = [...byBrand.entries()].map(([brand, list]) => {
        const prices = list.map((r) => r.current_price);
        const changes = list.map((r) => r.change_pct).filter((c): c is number => c != null).sort((a, b) => a - b);
        const median = changes.length ? changes[Math.floor(changes.length / 2)] : null;
        return {
          brand,
          brand_id: list[0].brand_id,
          is_own: list.some((r) => r.is_own_brand),
          model_count: list.length,
          avg_price: Math.round(prices.reduce((a, b) => a + b, 0) / prices.length),
          min_price: Math.min(...prices),
          median_change_pct: median != null ? Math.round(median * 100) / 100 : null,
        };
      });
      out.sort((a, b) => (a.is_own === b.is_own ? b.model_count - a.model_count : a.is_own ? -1 : 1));
      return out;
    }),
};
