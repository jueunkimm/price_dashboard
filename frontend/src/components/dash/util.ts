// 디자인 핸드오프 공용 유틸 — 합성 추세·스파크라인 좌표·색상 토큰

// 색상(디자인 토큰) — 인라인 스타일/SVG stroke 용
export const C = {
  up: "#c0473c", // 상승/비쌈
  down: "#3a6aa8", // 하락/저렴
  ink: "#1c1c22",
  brand: "#5b57d6",
  neutralSpark: "#a6abb6",
  upTint: "#fbecea",
  downTint: "#e9f0f8",
} as const;

// 비교 차트 팔레트(최대 5)
export const PALETTE = ["#3a6aa8", "#c0473c", "#5b57d6", "#2f8f6b", "#c98a2b"];

export const chgColor = (n: number | null | undefined) =>
  n == null || n === 0 ? C.neutralSpark : n > 0 ? C.up : C.down;

// 변동률(chg)을 반영해 시작 100 → 끝까지 자연스러운 합성 추세(결정론적).
// 실제 시계열이 없는 카테고리/포지셔닝 스파크라인용(핸드오프 mkTrend 동일 로직).
export function synthTrend(chg: number, n = 14, seed = 1): number[] {
  const pts: number[] = [];
  const end = 100 + (chg || 0) * 0.55;
  let s = (seed || 1) * 7 + 11;
  const rnd = () => {
    s = (s * 9301 + 49297) % 233280;
    return s / 233280;
  };
  const amp = Math.max(1.6, Math.abs(end - 100) * 0.22);
  for (let i = 0; i < n; i++) {
    const t = i / (n - 1);
    const e = t * t * (3 - 2 * t); // ease-in-out
    const base = 100 + (end - 100) * e;
    pts.push(+(base + (rnd() - 0.5) * amp).toFixed(2));
  }
  return pts;
}

// 값 배열 → SVG polyline points(min–max 정규화, 상하 패딩 pad)
export function sparkPoints(vals: number[], w: number, h: number, pad = 3): string {
  if (vals.length < 2) return "";
  const mn = Math.min(...vals);
  const mx = Math.max(...vals);
  const rng = mx - mn || 1;
  return vals
    .map((v, i) => {
      const x = (i / (vals.length - 1)) * (w - pad * 2) + pad;
      const y = h - pad - ((v - mn) / rng) * (h - pad * 2);
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
}
