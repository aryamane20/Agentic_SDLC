# PLANR — frontend

Vite + React 19 + TypeScript + Tailwind CSS, with **shadcn-style** layout (`components.json`, `@/components/ui`, `@/lib/utils`).

## Why `@/components/ui`?

The [shadcn/ui](https://ui.shadcn.com/) CLI and docs assume primitives and registry components live under `components/ui` with the `@/` alias. Keeping that path lets you run `npx shadcn@latest add …` without reconfiguring projects.

## Scripts

```bash
cd frontend
npm install
npm run dev      # http://localhost:5180 (not 5173 — avoids clashing with other Vite apps)
npm run build
```

## Landing

- **Particle text effect** — `src/components/ui/particle-text-effect.tsx` (21st.dev / KAINXU-style canvas). Vite build drops Next’s `"use client"` directive; animation cleans up on unmount.
- **Button** — shadcn-compatible variant in `src/components/ui/button.tsx`.
- **Icons** — `lucide-react`.

## Add more shadcn components

```bash
cd frontend
npx shadcn@latest add card dialog sheet
```

Ensure `components.json` paths match this repo (already set).
