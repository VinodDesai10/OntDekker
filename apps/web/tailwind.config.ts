import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/views/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/state/**/*.{js,ts,jsx,tsx}",
    "./src/router/**/*.{js,ts,jsx,tsx}",
    "./src/contexts/**/*.{js,ts,jsx,tsx}",
    "./src/hooks/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      // ----------------------------------------------------------------
      // OntDekker design token colors (from design system spec)
      // ----------------------------------------------------------------
      colors: {
        canvas: "#FBF9F4",
        card: "#FCFBF9",
        "border-sand": "#EAE7DF",
        ink: "#0A0A0A",
        charcoal: "#374151",
        "muted-slate": "#9CA3AF",
        "moss-green": "#059669",
        "ozone-blue": "#1D4ED8",
        "amber-ochre": "#B45309",
        // Full-scale forest for verification badges
        "forest-dark": "#0F5132",
      },

      // ----------------------------------------------------------------
      // Typography
      // ----------------------------------------------------------------
      fontFamily: {
        // Inter is loaded via next/font and injected as a CSS variable
        sans: ["var(--font-inter)", "system-ui", "sans-serif"],
        mono: ["var(--font-jetbrains-mono)", "ui-monospace", "monospace"],
      },

      // ----------------------------------------------------------------
      // Border radius (from design system)
      // ----------------------------------------------------------------
      borderRadius: {
        "4xl": "2rem",   // hero cards
        "3xl": "1.5rem", // standard cards
        "2xl": "1rem",   // buttons / inputs
        xl: "0.75rem",
      },

      // ----------------------------------------------------------------
      // Box shadows (minimal — border-first approach)
      // ----------------------------------------------------------------
      boxShadow: {
        xs: "0 1px 2px 0 rgb(0 0 0 / 0.04)",
        sm: "0 2px 4px 0 rgb(0 0 0 / 0.06)",
      },

      // ----------------------------------------------------------------
      // Max widths for layout containers
      // ----------------------------------------------------------------
      maxWidth: {
        "container": "64rem", // max-w-5xl equivalent (1024px)
      },

      // ----------------------------------------------------------------
      // Animation tokens (from motion design spec)
      // ----------------------------------------------------------------
      transitionDuration: {
        instant: "100ms",
        responsive: "200ms",
        medium: "300ms",
        intimate: "450ms",
      },

      transitionTimingFunction: {
        standard: "cubic-bezier(0.4,0,0.2,1)",
        decelerate: "cubic-bezier(0,0,0.2,1)",
        accelerate: "cubic-bezier(0.4,0,1,1)",
        spring: "cubic-bezier(0.34,1.56,0.64,1)",
      },
    },
  },
  plugins: [],
};

export default config;
