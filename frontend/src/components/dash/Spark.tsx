import { sparkPoints } from "./util";

// 경량 인라인 SVG 스파크라인 — 디자인 핸드오프(랭킹/카테고리/포지셔닝 추세)
export default function Spark({
  vals,
  color,
  w = 76,
  h = 24,
}: {
  vals: number[];
  color: string;
  w?: number;
  h?: number;
}) {
  const pts = sparkPoints(vals, w, h);
  return (
    <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`} className="block">
      {pts && (
        <polyline
          points={pts}
          fill="none"
          stroke={color}
          strokeWidth="1.6"
          strokeLinejoin="round"
          strokeLinecap="round"
        />
      )}
    </svg>
  );
}
