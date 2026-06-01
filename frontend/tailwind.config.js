/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // 자사(쿠쿠) 강조색
        own: "#7c3aed",
        up: "#dc2626", // 상승 빨강
        down: "#2563eb", // 하락 파랑
      },
    },
  },
  plugins: [],
};
