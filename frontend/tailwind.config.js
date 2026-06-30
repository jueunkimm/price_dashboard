/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // 디자인 토큰(클로드 디자인 핸드오프) — 한국 관례: 빨강=상승/비쌈, 파랑=하락/저렴
        own: "#5b57d6", // 브랜드(쿠쿠)/활성
        up: "#c0473c", // 상승/비쌈 빨강
        down: "#3a6aa8", // 하락/저렴 파랑
        ink: "#1c1c22", // 강조 텍스트
        page: "#f4f4f6", // 페이지 배경
      },
      fontFamily: {
        sans: [
          "Pretendard",
          "-apple-system",
          "BlinkMacSystemFont",
          "Segoe UI",
          "Roboto",
          "Noto Sans KR",
          "sans-serif",
        ],
      },
    },
  },
  plugins: [],
};
