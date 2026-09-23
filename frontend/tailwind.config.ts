import type {Config} from 'tailwindcss';
import tailwindcssAnimate from 'tailwindcss-animate';

export default {
  darkMode: ['class'],
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    container: {center: true, padding: '1.25rem', screens: {'2xl': '1440px'}},
    extend: {
      colors: {
        border: 'hsl(var(--border))',
        input: 'hsl(var(--input))',
        ring: 'hsl(var(--ring))',
        background: 'hsl(var(--background))',
        foreground: 'hsl(var(--foreground))',
        card: {DEFAULT: 'hsl(var(--card))', foreground: 'hsl(var(--card-foreground))'},
        primary: {DEFAULT: 'hsl(var(--primary))', foreground: 'hsl(var(--primary-foreground))'},
        secondary: {DEFAULT: 'hsl(var(--secondary))', foreground: 'hsl(var(--secondary-foreground))'},
        muted: {DEFAULT: 'hsl(var(--muted))', foreground: 'hsl(var(--muted-foreground))'},
        accent: {DEFAULT: 'hsl(var(--accent))', foreground: 'hsl(var(--accent-foreground))'},
        destructive: {DEFAULT: 'hsl(var(--destructive))', foreground: 'hsl(var(--destructive-foreground))'}
      },
      borderRadius: {xl: '1rem', '2xl': '1.25rem'},
      fontFamily: {sans: ['Inter', 'system-ui', 'sans-serif'], mono: ['JetBrains Mono', 'ui-monospace', 'monospace']}
    }
  },
  plugins: [tailwindcssAnimate]
} satisfies Config;
