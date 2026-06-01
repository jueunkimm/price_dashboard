export const won = (n: number | null | undefined) =>
  n == null ? "-" : "₩" + n.toLocaleString("ko-KR");

export const pct = (n: number | null | undefined) =>
  n == null ? "-" : `${n > 0 ? "+" : ""}${n.toFixed(2)}%`;

// 상승=빨강 / 하락=파랑 (기획서 디자인 원칙)
export const changeColor = (n: number | null | undefined) =>
  n == null ? "text-slate-400" : n > 0 ? "text-up" : n < 0 ? "text-down" : "text-slate-500";

export const arrow = (n: number | null | undefined) =>
  n == null ? "" : n > 0 ? "▲" : n < 0 ? "▼" : "─";
