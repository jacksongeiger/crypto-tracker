import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // ── Coinbase-themed tokens ──
        brand: {
          50: "#EBF1FF",
          100: "#D6E3FF",
          200: "#ADC6FF",
          300: "#7FA4FF",
          400: "#4F7BFF",
          500: "#0052FF",
          600: "#0040C2",
          700: "#002E8A",
          800: "#001E5C",
        },
        ink: {
          DEFAULT: "#0A0B0D",
          muted: "#5B616E",
          subtle: "#8A8F98",
          disabled: "#B1B5BC",
        },
        surface: {
          DEFAULT: "#FFFFFF",
          raised: "#FAFBFC",
          muted: "#F5F7FA",
        },
        line: {
          subtle: "#EAECF0",
          DEFAULT: "#D7DBE0",
          strong: "#A8AEB7",
        },
        success: {
          DEFAULT: "#05B169",
          tint: "#E6F7EE",
        },
        danger: {
          DEFAULT: "#DF5F67",
          tint: "#FCEDEE",
        },
        warning: {
          DEFAULT: "#F0B90B",
          tint: "#FEF7E2",
        },

        // ── shadcn shims (keep for any installed components) ──
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        destructive: "hsl(var(--destructive))",
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
      },
      borderRadius: {
        sm: "6px",
        md: "10px",
        lg: "14px",
      },
      fontFamily: {
        sans: ["var(--font-inter)", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "SFMono-Regular", "monospace"],
      },
      fontSize: {
        display: ["2.75rem", { lineHeight: "1.1", letterSpacing: "-0.025em" }],
        h1: ["2.125rem", { lineHeight: "1.18", letterSpacing: "-0.02em" }],
        h2: ["1.625rem", { lineHeight: "1.23", letterSpacing: "-0.015em" }],
        h3: ["1.25rem", { lineHeight: "1.4", letterSpacing: "-0.01em" }],
        bodyLg: ["1.1875rem", { lineHeight: "1.65" }],
        body: ["1rem", { lineHeight: "1.625" }],
        bodySm: ["0.875rem", { lineHeight: "1.55" }],
        caption: ["0.75rem", { lineHeight: "1.5", letterSpacing: "0.04em" }],
        mono: ["0.8125rem", { lineHeight: "1.55" }],
      },
      boxShadow: {
        sm: "0 1px 2px rgba(10,11,13,0.04)",
        md: "0 4px 12px rgba(10,11,13,0.08)",
        brandRing: "0 0 0 4px rgba(0,82,255,0.12)",
      },
      transitionTimingFunction: {
        coinbase: "cubic-bezier(0.16, 1, 0.3, 1)",
      },
      transitionDuration: {
        DEFAULT: "150ms",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};

export default config;
