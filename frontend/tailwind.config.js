/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        mars: {
          dark: "#0b0c10",
          base: "#1f2833",
          red: "#c1440e",
          rust: "#e77d22",
          sand: "#e0a96d",
          glow: "#ff5722",
        },
        hud: {
          cyan: "#45f3ff",
          amber: "#ffb703",
          red: "#ff3366",
          green: "#00f59b",
          panel: "rgba(11, 14, 21, 0.85)",
          border: "rgba(69, 243, 255, 0.25)"
        }
      },
      fontFamily: {
        mono: ['"JetBrains Mono"', 'Menlo', 'monospace'],
        display: ['Orbitron', 'sans-serif'],
      }
    },
  },
  plugins: [],
}
