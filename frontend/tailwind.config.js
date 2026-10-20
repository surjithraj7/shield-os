/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: ["class", "[data-theme='dark']"],
  content: [
    "./src/**/*.{js,ts,jsx,tsx}",
    "./index.html",
  ],
  theme: {
    extend: {
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          cyan: "#00f0ff",
          magenta: "#ff00e5",
          violet: "#7c3aed",
          green: "#00ff88",
          yellow: "#ffe600",
          red: "#ff2d6f",
          orange: "#ff8800",
        },
        success: "#00ff88",
        warning: "#ffe600",
        error: "#ff2d6f",
        info: "#00f0ff",
        surface: {
          0: "#060612",
          1: "#0a0a1e",
          2: "#0e0e28",
          3: "#121232",
        },
        card: "hsl(var(--card))",
        popover: "hsl(var(--popover))",
        chart: {
          1: "#00f0ff",
          2: "#ff00e5",
          3: "#7c3aed",
          4: "#00ff88",
        },
      },
      fontFamily: {
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'Cascadia Code', 'monospace'],
      },
      borderRadius: {
        lg: "var(--radius-lg)",
        md: "var(--radius-md)",
        sm: "var(--radius-sm)",
      },
      keyframes: {
        "accordion-down": {
          from: { height: "0" },
          to: { height: "var(--radix-accordion-height)" },
        },
        "accordion-up": {
          from: { height: "var(--radix-accordion-height)" },
          to: { height: "0" },
        },
        "glow-pulse": {
          "0%, 100%": { boxShadow: "0 0 20px rgba(0, 240, 255, 0.25)" },
          "50%": { boxShadow: "0 0 30px rgba(0, 240, 255, 0.4)" },
        },
        "float": {
          "0%, 100%": { transform: "translateY(0)" },
          "50%": { transform: "translateY(-4px)" },
        },
      },
      animation: {
        "accordion-down": "accordion-down 0.2s ease-out",
        "accordion-up": "accordion-up 0.2s ease-out",
        "glow-pulse": "glow-pulse 3s ease-in-out infinite",
        "float": "float 3s ease-in-out infinite",
      },
    },
  },
  plugins: [
    require("tailwindcss-animate"),
    function ({ addUtilities }) {
      addUtilities({
        ".glass": {
          background: "rgba(8, 8, 28, 0.75)",
          backdropFilter: "blur(16px)",
          WebkitBackdropFilter: "blur(16px)",
          border: "1px solid rgba(0, 240, 255, 0.12)",
        },
        ".glass-hover:hover": {
          background: "rgba(12, 12, 35, 0.85)",
          borderColor: "rgba(0, 240, 255, 0.25)",
        },
        ".neon-text": {
          textShadow: "0 0 10px rgba(0, 240, 255, 0.5), 0 0 20px rgba(0, 240, 255, 0.3)",
        },
        ".neon-border": {
          boxShadow: "0 0 15px rgba(0, 240, 255, 0.15), inset 0 0 15px rgba(0, 240, 255, 0.05)",
        },
        ".bg-pattern-cyber": {
          backgroundImage:
            "radial-gradient(circle at 20% 20%, rgba(0, 240, 255, 0.06), transparent 50%), radial-gradient(circle at 80% 80%, rgba(124, 58, 237, 0.05), transparent 50%)",
        },
      });
    },
  ],
};
