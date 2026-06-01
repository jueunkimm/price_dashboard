// 백엔드 API 클라이언트 (vite proxy 로 /api → :8000)

export interface CategoryOverview {
  category_id: number;
  category_name: string;
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

export interface SegPositioning {
  category_id: number;
  category_name: string;
  capacity_band: string;
  own_avg_price: number;
  segment_avg_price: number;
  segment_size: number;
  own_product_count: number;
  positioning_pct: number | null;
}

export interface BrandRow {
  brand: string;
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
  brands: { id: number; name: string; is_own: boolean }[];
  malls: { name: string; count: number }[];
  price_min: number;
  price_max: number;
}

export interface FilteredProduct {
  product_id: number;
  model_name: string;
  category_name: string;
  brand: string;
  capacity_band: string | null;
  mall: string | null;
  is_own_brand: boolean;
  is_rental: boolean;
  current_price: number;
  change_pct: number | null;
}

export interface ProductFilters {
  category_id?: number;
  brand_id?: number;
  capacity_band?: string;
  min_price?: number;
  max_price?: number;
  own_only?: boolean;
  exclude_rental?: boolean;
  q?: string;
  mall?: string;
}

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

function applyFilters(rows: PRow[], f: ProductFilters, ownOnly: boolean): PRow[] {
  const excludeRental = f.exclude_rental !== false;
  const filtered = rows.filter((p) => {
    if (excludeRental && p.is_rental) return false;
    if ((ownOnly || f.own_only) && !p.is_own_brand) return false;
    if (f.category_id && p.category_id !== f.category_id) return false;
    if (f.brand_id != null && p.brand_id !== f.brand_id) return false;
    if (f.capacity_band && p.capacity_band !== f.capacity_band) return false;
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
  positioning: () => loadJSON<Positioning[]>("positioning"),
  positioningSegmented: () => loadJSON<SegPositioning[]>("positioning_segmented"),
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
      applyFilters(rows, f, !!f.own_only)
        .sort((a, b) => a.current_price - b.current_price)
        .slice(0, 200)
    ),

  filterOptions: (categoryId?: number) =>
    loadJSON<PRow[]>("products").then((rows) => {
      const inCat = categoryId ? rows.filter((p) => p.category_id === categoryId) : rows;
      const bands = [...new Set(inCat.map((p) => p.capacity_band).filter(Boolean))].sort() as string[];
      const brandMap = new Map<number, { id: number; name: string; is_own: boolean }>();
      for (const p of inCat) if (p.brand_id != null) brandMap.set(p.brand_id, { id: p.brand_id, name: p.brand, is_own: p.is_own_brand });
      const brands = [...brandMap.values()].sort((a, b) => (a.is_own === b.is_own ? a.name.localeCompare(b.name) : a.is_own ? -1 : 1));
      const mallCount = new Map<string, number>();
      for (const p of inCat) if (p.mall) mallCount.set(p.mall, (mallCount.get(p.mall) ?? 0) + 1);
      const malls = [...mallCount.entries()].sort((a, b) => b[1] - a[1]).map(([name, count]) => ({ name, count }));
      const prices = inCat.map((p) => p.current_price);
      return {
        capacity_bands: bands,
        brands,
        malls,
        price_min: prices.length ? Math.min(...prices) : 0,
        price_max: prices.length ? Math.max(...prices) : 0,
      } as FilterOptions;
    }),

  brandComparison: (categoryId: number, f: ProductFilters = {}) =>
    loadJSON<PRow[]>("products").then((rows) => {
      // own_only/brand는 비교 위해 미적용, 용량·몰·가격·렌탈 필터는 제품 목록과 동일
      const items = applyFilters(rows.filter((p) => p.category_id === categoryId), {
        capacity_band: f.capacity_band,
        mall: f.mall,
        min_price: f.min_price,
        max_price: f.max_price,
        exclude_rental: f.exclude_rental,
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
