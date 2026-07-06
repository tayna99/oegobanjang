/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'Pretendard', 'system-ui', 'Apple SD Gothic Neo', 'Noto Sans KR', 'sans-serif'],
      },
      colors: {
        brand: {
          50: '#eff6ff',
          100: '#dbeafe',
          500: '#2563eb',
          600: '#1d4ed8',
          700: '#1e40af',
        },
        mint: '#00a6a6',
      },
      boxShadow: {
        soft: '0 12px 30px rgba(15, 23, 42, 0.06)',
      }
    },
  },
  plugins: [],
};
