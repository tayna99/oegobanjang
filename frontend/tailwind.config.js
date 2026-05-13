/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./features/**/*.{ts,tsx}"],
  corePlugins: {
    preflight: false,
  },
  theme: {
    extend: {
      fontFamily: {
        sans: ["Pretendard", "Inter", "system-ui", "Apple SD Gothic Neo", "Noto Sans KR", "sans-serif"],
      },
      boxShadow: {
        soft: "0 12px 30px rgba(15, 23, 42, 0.06)",
      },
      colors: {
        brand: {
          50: "#eff6ff",
          100: "#dbeafe",
          500: "#2563eb",
          600: "#1d4ed8",
          700: "#1e40af",
        },
        mint: "#00a6a6",
      },
    },
  },
  plugins: [],
};
