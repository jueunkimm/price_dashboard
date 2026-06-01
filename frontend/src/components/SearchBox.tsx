import { useEffect, useRef, useState } from "react";
import { api, type ProductRow } from "../api";

// 제품 검색(모델명) — 선택 시 추세 차트로 연결
export default function SearchBox({
  ownOnly,
  onSelect,
}: {
  ownOnly: boolean;
  onSelect: (productId: number) => void;
}) {
  const [q, setQ] = useState("");
  const [results, setResults] = useState<ProductRow[]>([]);
  const [open, setOpen] = useState(false);
  const boxRef = useRef<HTMLDivElement>(null);

  // 디바운스 검색
  useEffect(() => {
    const term = q.trim();
    if (term.length < 2) {
      setResults([]);
      return;
    }
    const t = setTimeout(() => {
      api
        .products(term, ownOnly, 12)
        .then((r) => {
          setResults(r);
          setOpen(true);
        })
        .catch(() => setResults([]));
    }, 250);
    return () => clearTimeout(t);
  }, [q, ownOnly]);

  // 외부 클릭 시 닫기
  useEffect(() => {
    const h = (e: MouseEvent) => {
      if (boxRef.current && !boxRef.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", h);
    return () => document.removeEventListener("mousedown", h);
  }, []);

  const pick = (p: ProductRow) => {
    onSelect(p.product_id);
    setOpen(false);
    setQ("");
  };

  return (
    <div ref={boxRef} className="relative w-full max-w-xs">
      <input
        value={q}
        onChange={(e) => setQ(e.target.value)}
        onFocus={() => results.length && setOpen(true)}
        placeholder="모델명 검색…"
        className="w-full text-sm px-3 py-1.5 rounded-lg border border-slate-200 focus:outline-none focus:ring-1 focus:ring-own bg-white"
      />
      {open && results.length > 0 && (
        <ul className="absolute z-20 mt-1 w-full max-h-80 overflow-y-auto bg-white rounded-lg border border-slate-200 shadow-lg">
          {results.map((p) => (
            <li
              key={p.product_id}
              onClick={() => pick(p)}
              className="px-3 py-2 text-sm hover:bg-slate-50 cursor-pointer border-b border-slate-50 last:border-0"
            >
              {p.is_own_brand && (
                <span className="text-[10px] bg-own/10 text-own px-1 py-0.5 rounded mr-1">쿠쿠</span>
              )}
              {p.is_rental && (
                <span className="text-[10px] bg-amber-100 text-amber-700 px-1 py-0.5 rounded mr-1">렌탈</span>
              )}
              <span className="text-slate-700">{p.model_name}</span>
            </li>
          ))}
        </ul>
      )}
      {open && q.trim().length >= 2 && results.length === 0 && (
        <div className="absolute z-20 mt-1 w-full bg-white rounded-lg border border-slate-200 shadow-lg px-3 py-2 text-sm text-slate-400">
          검색 결과 없음
        </div>
      )}
    </div>
  );
}
