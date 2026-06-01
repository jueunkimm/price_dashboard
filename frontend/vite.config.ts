import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// base: "./" → 상대 경로 → GitHub Pages 프로젝트 경로(/repo/)·루트 어디에 올려도 동작.
// 데이터는 정적 /data/*.json (백엔드 없음). 로컬 dev는 public/data 를 그대로 서빙.
export default defineConfig({
  base: "./",
  plugins: [react()],
  server: { port: 5173 },
});
