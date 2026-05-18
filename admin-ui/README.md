# Nébula Admin UI (Next.js)

Panel administrativo premium en **React + Next.js + Tailwind + Framer Motion + Lucide**.

## Desarrollo

```bash
cd admin-ui
npm install
npm run dev
```

Abre [http://localhost:3000](http://localhost:3000).

## Integración con Flask

El backend actual sirve el panel en `/admin` y `/analytics` con plantillas Jinja y `static/css/admin-premium.css`.

Este paquete es la **versión React** para migración gradual: conecta las mismas métricas vía API (`/analytics/export` o endpoints REST futuros).

## Estructura

- `app/` — rutas App Router
- `components/admin/` — Sidebar, Topbar, KPI, shell
- `lib/utils.ts` — utilidades `cn()`
