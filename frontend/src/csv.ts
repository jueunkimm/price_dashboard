// CSV 내보내기 — Excel에서 한글이 깨지지 않도록 UTF-8 BOM 부착

type Col<T> = { key: keyof T; label: string };

function cell(v: unknown): string {
  if (v == null) return "";
  const s = String(v);
  // 쉼표/따옴표/개행 포함 시 큰따옴표 escape
  return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

export function downloadCsv<T>(filename: string, cols: Col<T>[], rows: T[]): void {
  const header = cols.map((c) => cell(c.label)).join(",");
  const body = rows.map((r) => cols.map((c) => cell(r[c.key])).join(",")).join("\n");
  const csv = "﻿" + header + "\n" + body; // BOM
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

// 공통 내보내기 버튼 스타일 클래스
export const csvBtnClass =
  "text-[11px] px-2 py-0.5 rounded border border-slate-200 text-slate-500 hover:bg-slate-50";
