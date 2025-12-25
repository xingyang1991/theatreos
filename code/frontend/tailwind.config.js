/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // TheatreOS 品牌色系 - 剧场暗色调
        theatre: {
          bg: '#0a0a0f',           // 深黑背景
          surface: '#12121a',      // 卡片表面
          border: '#1f1f2e',       // 边框
          muted: '#6b6b7a',        // 次要文字
          text: '#e4e4e7',         // 主要文字
          accent: '#c9a962',       // 金色强调（剧场感）
          danger: '#ef4444',       // 危险/警告
          success: '#22c55e',      // 成功
        },
        // Ring 圈层色彩
        ring: {
          c: '#6366f1',            // RingC - 远观 (靛蓝)
          b: '#8b5cf6',            // RingB - 靠近 (紫色)
          a: '#f59e0b',            // RingA - 核心 (琥珀)
        },
        // 门类型色彩
        gate: {
          public: '#3b82f6',       // 公共门 (蓝)
          fate: '#ec4899',         // 命运门 (粉)
          council: '#f59e0b',      // 议会门 (金)
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        display: ['Playfair Display', 'serif'],  // 剧场标题字体
        mono: ['JetBrains Mono', 'monospace'],
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'countdown': 'countdown 1s ease-in-out infinite',
        'fade-in': 'fadeIn 0.3s ease-out',
        'slide-up': 'slideUp 0.3s ease-out',
        'glow': 'glow 2s ease-in-out infinite alternate',
      },
      keyframes: {
        countdown: {
          '0%, 100%': { transform: 'scale(1)' },
          '50%': { transform: 'scale(1.05)' },
        },
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(10px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        glow: {
          '0%': { boxShadow: '0 0 5px rgba(201, 169, 98, 0.5)' },
          '100%': { boxShadow: '0 0 20px rgba(201, 169, 98, 0.8)' },
        },
      },
    },
  },
  plugins: [],
}
