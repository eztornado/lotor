# 🍀 Bonoloto — Generador inteligente de carteras

Módulo de LoTor que genera **entre 1 y 10 apuestas de Bonoloto** a partir del
histórico completo de sorteos (1988 → hoy) y de un conjunto de algoritmos de
optimización. Está disponible tanto en el **backend** (API REST) como en el
**frontend** (página `/bonoloto`).

> ⚠️ **Aviso**: la lotería es un juego de azar. Ningún algoritmo puede predecir
> el resultado ni garantizar premios. La probabilidad de acertar 6 números con
> una apuesta es **1 entre 13.983.816** y no cambia con ninguna estrategia. Lo
> que optimiza esta herramienta es la **cobertura** de la cartera y el **riesgo
> de compartir** un gran premio, no el azar.

---

## 📋 Reglas del juego

| Regla | Valor |
| --- | --- |
| Números por apuesta | 6 |
| Rango de números | 1 – 49 |
| Complementario | 1 número extra (para la 2ª categoría) |
| Reintegro | 1 dígito (0 – 9) |
| Días de sorteo | Lunes a sábado |
| Precio de la apuesta | 0,50 € |

### Categorías de premio

| Categoría | Aciertos | Combinaciones favorables | Probabilidad por apuesta |
| --- | --- | --- | --- |
| 1ª | 6 | 1 | 1 / 13.983.816 |
| 2ª | 5 + complementario | 6 | 1 / 2.330.636 |
| 3ª | 5 | 252 | 1 / 55.491 |
| 4ª | 4 | 13.545 | 1 / 1.032 |
| 5ª | 3 | 246.820 | 1 / 57 |
| Reintegro | dígito igual | 10 de 10 | 1 / 10 |

Categorías agregadas usadas en la interfaz:

- **3+** → 3, 4, 5, 5+complementario y 6: `260.624 / 13.983.816` (≈ 1,86 %)
- **4+** → 4, 5, 5+complementario y 6: `13.804 / 13.983.816` (≈ 0,099 %)
- **5+** → 5, 5+complementario y 6: `259 / 13.983.816`

---

## 🗂️ Datos históricos

- **Fuente**: hojas públicas de [Lotoideas](https://www.lotoideas.com/) con los
  resultados oficiales de **SELAE**.
- **Fichero**: `backend/data/raw/bonoloto_historical.csv`
- **Columnas**: `date,n1,n2,n3,n4,n5,n6,complementario,reintegro,source`
- **Cobertura**: desde el 28/02/1988 (≈ 9.420 sorteos). Antes de ~2015 puede
  faltar el `reintegro`; el generador lo tolera.
- **Actualización**:
  - Script reproducible: `python backend/scripts/import_bonoloto.py` (admite
    `--offline` para no salir a la red).
  - API: `GET/POST /api/v1/bonoloto/refresh`.
- El histórico está **cacheado** en memoria; si cambia el CSV, la siguiente
  generación usa los datos nuevos.

### Próximo sorteo

`next_bonoloto_date()` toma la fecha del último sorteo y avanza al siguiente día
natural, **saltando el domingo** (no hay sorteo). Si el último sorteo es del
sábado, el próximo es el lunes.

---

## 🧠 Cómo se genera la cartera

El objetivo no es "predecir" (imposible) sino construir la mejor **cartera** de
10 apuestas frente a una elección ingenua. Se combinan cinco bloques:

### 1. Modelo de propensión por número

Para cada número 1–49 se combinan cuatro señales:

- **Frecuencia a largo plazo** (histórico completo).
- **Frecuencia reciente** con vida media de 45 días.
- **Retraso** (sorteos desde la última aparición).
- **Afinidad de pares** (con qué números suele salir).

Se aplica **suavizado bayesiano** y se limita el peso máximo de cada número para
**evitar el sobreajuste**: en una lotería uniforme el ruido domina a corto plazo.

### 2. Filtro estructural (aprendido del histórico)

Cada combinación se puntúa según lo "típica" que es respecto a las distribuciones
reales del histórico:

- suma de los 6 números,
- paridad (impares / pares),
- bajos / altos,
- distribución por **décadas**,
- **consecutivos**,
- **terminaciones**.

### 3. Penalización anti-popularidad

Se penalizan las combinaciones que juega mucha gente:

- números ≤ 31 (fechas de nacimiento),
- progresiones aritméticas,
- patrones geométricos o "bonitos".

Es la **única palanca real** para mejorar el importe esperado de un gran premio:
si el premio cae en una combinación muy jugada, se reparte entre más acertantes.

### 4. Optimización de la cartera

Se generan candidatos (**68 % ponderados por el modelo / 32 % uniformes**),
se construye una columna vertebral de cobertura y se optimiza con **búsqueda
greedy + búsqueda local** maximizando una función de calidad que pondera:

| Peso | Componente |
| --- | --- |
| quality | calidad estadística media |
| numbers | números distintos cubiertos |
| pairs | pares distintos cubiertos |
| triples | tríos distintos cubiertos |
| overlap | penalización por solapamiento |
| balance | equilibrio de aparición de números |
| popularity | penalización de popularidad |

Cuatro estrategias ajustan esos pesos:

| Estrategia | Etiqueta | Enfoque |
| --- | --- | --- |
| `big_prize` *(por defecto)* | Máximo premio | Cobertura de pares/tríos + baja popularidad |
| `balanced` | Equilibrada | Reparte calidad estadística y cobertura |
| `coverage` | Máxima cobertura | Maximiza números, pares y tríos distintos |
| `statistical` | Estadística pura | Prioriza los números con mayor propensión |

### 5. Cobertura y reintegros

- **count ≤ 8**: se buscan apuestas **disjuntas** (sin solapamiento) para
  maximizar la probabilidad de acertar en categorías bajas.
- **count 9–10**: se persigue la **cobertura completa de los 49 números**.
- **Reintegros**: se asignan dígitos **distintos**. Con 10 apuestas se cubren los
  10 dígitos, garantizando recuperar el importe de una de ellas.

> Si no se indica `seed`, se usa una semilla determinista derivada del último
> sorteo + estrategia + número de apuestas (resultado reproducible por sorteo).
> La semilla se devuelve en la respuesta.

---

## 📡 API (backend)

Base: `/api/v1/bonoloto`

| Método | Ruta | Descripción |
| --- | --- | --- |
| `GET` | `/meta` | Reglas, estado del dataset y estrategias |
| `GET` | `/next-draw` | Fecha del próximo sorteo |
| `GET` | `/history?limit=50` | Últimos sorteos (1–500) |
| `GET` | `/stats` | Estadísticas y probabilidades del modelo |
| `POST` | `/generate` | Genera la cartera (cuerpo JSON) |
| `GET` | `/generate?count=10&strategy=big_prize&seed=...` | Alias GET |
| `GET/POST` | `/refresh` | Actualiza el histórico desde Lotoideas/SELAE |

### Petición de generación

```json
{
  "count": 10,
  "strategy": "big_prize",
  "seed": 123456789
}
```

- `count`: entero 1–10 (por defecto 10).
- `strategy`: `big_prize` \| `balanced` \| `coverage` \| `statistical`.
- `seed`: opcional; si se omite, se deriva automáticamente.

### Respuesta (resumen)

```jsonc
{
  "game": { "name": "Bonoloto", "max_number": 49, "ticket_price_eur": 0.5, ... },
  "seed": 123456789,
  "strategy": "big_prize",
  "strategy_label": "Máximo premio",
  "dataset": {
    "total_draws": 9420,
    "date_range": { "from": "1988-02-28", "to": "2026-10-17" },
    "next_draw": "2026-10-19"
  },
  "combinations": [
    {
      "index": 1,
      "numbers": [4, 11, 23, 31, 38, 45],
      "reintegro": 3,
      "quality": 0.87,
      "quality_grade": "alta",
      "popularity": 0.08,
      "sum": 152,
      "odd": 4, "even": 2, "low": 3, "high": 3,
      "consecutive_pairs": 0,
      "tags": ["..."]
    }
  ],
  "portfolio": {
    "tickets": 10,
    "cost_eur": 5.0,
    "coverage": { "unique_numbers": 49, "numbers_pct": 100.0, ... },
    "overlap": { "average": 0.0, "max": 1 },
    "popularity": { "risk": "bajo", "low_popularity_tickets": 9 },
    "theoretical": {
      "prob_6": 7.15e-7,
      "prob_5_plus_complementario": 4.29e-6,
      "prob_5": 1.8e-5,
      "prob_4_plus": 0.000987,
      "prob_3_plus": 0.0186,
      "prob_reintegro": 1.0,
      "expected_matches": 2.57
    },
    "simulation": { "simulations": 200000, "prob_3_plus": 0.0185 },
    "reintegros": { "distinct": 10, "guaranteed_match": true }
  },
  "analysis": { "hot_numbers": [...], "overdue_numbers": [...], ... },
  "recommendations": ["..."],
  "disclaimer": "..."
}
```

---

## 🧮 Fórmulas de probabilidad

Para una cartera de `k` apuestas **distintas** y una categoría con `m`
combinaciones favorables de un total `N = 13.983.816`:

```
p(alguna apuesta en esa categoría) ≈ 1 - (1 - m/N)^k
```

- **Reintegro**: si las 10 apuestas usan los 10 dígitos, la probabilidad de
  coincidir al menos una vez es `1,0`.
- **Aciertos esperados** = `k · 6 · (6/49) ≈ k · 0,7347` (suma de aciertos de
  todas las apuestas frente a un sorteo).
- El **jackpot por apuesta** es siempre `1/13.983.816`; con `k` apuestas se
  multiplica por `k` (hasta ≈ `1/1.398.382` con 10 apuestas).

Además se ejecuta una **simulación Monte Carlo** (por defecto 200.000 sorteos)
sobre la cartera concreta para contrastar las probabilidades teóricas. Las
probabilidades de premio son **fijas por categoría** en Bonoloto, salvo el bote
de la 1ª categoría.

---

## 🖥️ Frontend

- Ruta: `/bonoloto` (`frontend/src/components/BonolotoPage.tsx`).
- Permite elegir **número de apuestas** (1–10) y **estrategia**, generar una
  cartera nueva (semilla aleatoria) y **copiar** las combinaciones.
- Muestra: próximo sorteo, coste, cobertura (números / pares / tríos), riesgo de
  compartir premio, probabilidades teóricas, simulación, análisis del histórico
  (calientes, retrasados, estructura, pares) y recomendaciones.
- Cliente API: `frontend/src/services/api.ts` → `bonolotoApi`.

---

## 🧪 Tests

```bash
cd backend
PYTHONPATH=. python -m pytest tests/test_bonoloto.py -q
```

Cubren: validez de las combinaciones, rangos, cobertura, reintegros, estrategias,
reproducibilidad con semilla, probabilidades y endpoints principales.

---

## 📐 Resumen matemático honesto

1. **No se puede predecir** una lotería uniforme; el generador no mejora la
   probabilidad por apuesta.
2. **Cobertura**: con más apuestas (y sobre todo disjuntas) aumenta la
   probabilidad de *algún* premio en categorías bajas.
3. **Anti-popularidad**: elegir combinaciones poco jugadas reduce el reparto del
   premio, que es la única vía real de mejorar el **importe esperado** de un gran
   premio.
4. **Reintegro**: cubrir los 10 dígitos con 10 apuestas garantiza recuperar uno.
