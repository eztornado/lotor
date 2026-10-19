# 🖥️ Arquitectura del frontend

LoTor es una aplicación **multi‑juego**: hoy soporta *El Gordo de la Primitiva* y
*Bonoloto*, y está preparada para añadir más juegos sin tocar la navegación.

```
frontend/
├── index.html
├── public/
│   └── favicon.svg
└── src/
    ├── main.tsx                 # Provider de Mantine + render
    ├── App.tsx                  # Router, layout y definición de rutas
    ├── games.ts                 # Registro de juegos (nav, color, rutas)
    ├── index.css
    ├── components/
    │   ├── layout/
    │   │   └── Header.tsx        # Cabecera + selector de juego + nav
    │   └── bonoloto/             # Componentes de UI de Bonoloto
    │       ├── Ball.tsx
    │       ├── CombinationCard.tsx
    │       ├── PortfolioOverview.tsx
    │       ├── ProbabilityPanel.tsx
    │       ├── SharingRiskPanel.tsx
    │       ├── AnalysisPanel.tsx
    │       ├── RecommendationsPanel.tsx
    │       ├── HowItWorks.tsx
    │       └── format.ts
    ├── pages/
    │   ├── HomePage.tsx          # Home multi‑juego (tarjeta por juego)
    │   ├── gordo/                # Páginas de El Gordo
    │   │   ├── PredictionPage.tsx
    │   │   ├── StatisticsPage.tsx
    │   │   ├── HistoryPage.tsx
    │   │   └── WeeklyCombinationsPage.tsx
    │   └── bonoloto/             # Páginas de Bonoloto
    │       ├── BonolotoPage.tsx      # Generador de carteras
    │       ├── BonolotoStatsPage.tsx
    │       └── BonolotoHistoryPage.tsx
    └── services/
        ├── client.ts             # Instancia axios (/api/v1)
        ├── gordo.ts              # Tipos + clientes de El Gordo
        ├── bonoloto.ts           # Tipos + cliente de Bonoloto
        └── api.ts                # Barrel: reexporta todo (compatibilidad)
```

## 🧭 Rutas

| Ruta | Página |
| --- | --- |
| `/` | Home multi‑juego |
| `/gordo/prediction` | Predicción El Gordo |
| `/gordo/statistics` | Estadísticas El Gordo |
| `/gordo/history` | Historial El Gordo |
| `/gordo/weekly-combinations` | 7 combinaciones semanales |
| `/bonoloto` | Generador Bonoloto |
| `/bonoloto/estadisticas` | Estadísticas Bonoloto |
| `/bonoloto/historial` | Historial Bonoloto |

Las rutas antiguas (`/prediction`, `/statistics`, `/history`,
`/weekly-combinations`) se redirigen a sus equivalentes bajo `/gordo`.

## 🎮 Registro de juegos (`src/games.ts`)

Cada juego se describe con `GameDefinition`:

```ts
{
  id, name, shortName, emoji, color,
  tagline, description, basePath,
  nav: [{ label, path, icon }, ...]
}
```

El `Header` y la `HomePage` se generan a partir de `GAMES`, de modo que la
navegación y las tarjetas de la home se actualizan solas.

### Añadir un juego nuevo

1. Añade una entrada a `GAMES` en `src/games.ts` (con su `basePath` y `nav`).
2. Crea sus páginas en `src/pages/<juego>/`.
3. Añade su cliente/tipos en `src/services/<juego>.ts` y reexpórtalos en
   `services/api.ts`.
4. Declara sus rutas en `src/App.tsx`.

## 🧩 Servicios

- `services/client.ts`: única instancia de axios con `baseURL = /api/v1`.
- `services/gordo.ts` y `services/bonoloto.ts`: tipos y clientes por juego.
- `services/api.ts`: barrel de compatibilidad; los imports antiguos
  (`import { bonolotoApi } from '../services/api'`) siguen funcionando.

## ✅ Verificación

```bash
cd frontend
npm install
npm run build      # tsc && vite build
npm run dev        # http://localhost:3000
```
