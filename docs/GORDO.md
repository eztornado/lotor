# 🎰 El Gordo de la Primitiva — Generador inteligente de carteras

Módulo de LoTor que genera **entre 1 y 10 apuestas de El Gordo de la Primitiva**
a partir del histórico completo de sorteos (2005 → hoy) y de un conjunto de
algoritmos de optimización. Está disponible en el **backend** (API REST) y en el
**frontend** (página `/gordo`).

> ⚠️ **Aviso**: la lotería es un juego de azar. Ningún algoritmo puede predecir
> el resultado ni garantizar premios. La probabilidad de acertar los 5 números y
> la clave con una apuesta es **1 entre 31.625.100** y no cambia con ninguna
> estrategia. Lo que optimiza esta herramienta es la **cobertura** de la cartera,
> el **riesgo de compartir** un gran premio y la **cobertura de la clave**
> (reintegro), no el azar.

---

## 📋 Reglas del juego

| Regla | Valor |
| --- | --- |
| Números por apuesta | 5 |
| Rango de números | 1 – 54 |
| Clave | 1 dígito (0 – 9) |
| Días de sorteo | Domingos |
| Precio de la apuesta | 1,50 € |
| Combinaciones de números | C(54, 5) = 3.162.510 |
| Apuestas posibles (números + clave) | 31.625.100 |

### Categorías de premio

| Categoría | Aciertos | Combinaciones favorables | Probabilidad por apuesta |
| --- | --- | --- | --- |
| 1ª | 5 + clave | 1 | 1 / 31.625.100 |
| 2ª | 5 | 9 | 1 / 3.513.900 |
| 3ª | 4 + clave | 245 | 1 / 129.082 |
| 4ª | 4 | 2.205 | 1 / 14.342 |
| 5ª | 3 + clave | 11.760 | 1 / 2.689 |
| 6ª | 3 | 105.840 | 1 / 299 |
| 7ª | 2 + clave | 184.240 | 1 / 172 |
| 8ª | 2 | 1.658.160 | 1 / 19,07 |

- **Alguna de las 8 categorías**: 1.962.460 / 31.625.100 = **6,2054 %**
  (≈ 1 entre 16,12) por apuesta.
- **Reintegro**: si la clave de la apuesta coincide con la clave ganadora se
  devuelven **1,50 €**, aunque no se acierte ningún número. Es **compatible**
  con cualquiera de las 8 categorías: una apuesta con 2 o más aciertos y la
  clave cobra premio **y** reintegro.
- **Algún retorno** (premio de categoría o reintegro) por apuesta:
  `1 − (1 − 0,062054) · (1 − 0,10)` = **15,5848 %**.

Categorías agregadas usadas en la interfaz (probabilidad de que la **mejor**
categoría de una apuesta sea al menos esa):

- **2+** → categorías 1 a 8: 1.962.460 / 31.625.100 ≈ **6,2054 %**.
- **3+** → categorías 1 a 6: 120.060 / 31.625.100 ≈ **0,3796 %**.
- **4+** → categorías 1 a 4: 2.460 / 31.625.100 ≈ **0,007779 %**.
- **5+** → categorías 1 y 2: 10 / 31.625.100 ≈ **0,0000316 %**.

---

## 🗂️ Datos históricos

- **Fuente**: hoja pública de [Lotoideas](https://www.lotoideas.com/) con los
  resultados oficiales de **SELAE**.
- **Fichero**: `backend/data/raw/gordo_historical.csv`
- **Columnas**: `date,n1,n2,n3,n4,n5,key_number,source`
- **Cobertura**: desde el **06/02/2005** (formato actual de 5 números + clave),
  con **1.123 sorteos** hasta el **18/10/2026**.
- **Fuentes registradas**: `manual_selae` (resultado añadido a mano) y
  `lotoideas_selae` (importado de la hoja pública).
- **Actualización**:
  - Script reproducible: `python backend/scripts/import_gordo.py` (admite
    `--offline` para no salir a la red).
  - API: `GET/POST /api/v1/gordo/refresh`.
- El histórico está **cacheado** en memoria; si cambia el CSV, la siguiente
  generación usa los datos nuevos.

### Próximo sorteo

`next_gordo_date()` toma la fecha del último sorteo y avanza al siguiente
**domingo**, con un corte de venta a las 21:00. El próximo sorteo tras el
18/10/2026 es el **25/10/2026**.

---

## 🧠 Cómo se genera la cartera

El objetivo no es "predecir" (imposible) sino construir la mejor **cartera** de
hasta 10 apuestas frente a una elección ingenua. Se combinan estos bloques:

### 1. Modelo de propensión por número

Para cada número 1–54 se combinan cuatro señales:

- **Frecuencia a largo plazo** (histórico completo).
- **Frecuencia reciente** con vida media configurable (por defecto 365 días).
- **Retraso** (sorteos desde la última aparición).
- **Afinidad de pares** (con qué números suele salir).

Se aplica **suavizado bayesiano** y se limita el peso de cada número para
**evitar el sobreajuste**: en una lotería uniforme el ruido domina a corto plazo.

### 2. Modelo de la clave (0–9)

La clave se puntúa con frecuencia histórica, tendencia reciente y retraso. Las
claves más probables se usan primero cuando hay menos de 10 apuestas; con 10
apuestas se cubren las 10 claves posibles.

### 3. Filtro estructural (aprendido del histórico)

Cada combinación se puntúa según lo "típica" que es respecto a las
distribuciones reales del histórico:

- suma de los 5 números,
- paridad (impares / pares),
- bajos / altos (≤ 27 / ≥ 28),
- distribución por **décadas** (1–9, 10–19, …, 50–54),
- **consecutivos**,
- **terminaciones** y progresiones aritméticas.

### 4. Penalización anti-popularidad

Se penalizan las combinaciones que juega mucha gente:

- números ≤ 31 (fechas de nacimiento),
- progresiones aritméticas,
- patrones geométricos o "bonitos".

Es la **única palanca real** para mejorar el importe esperado de un gran premio:
si el premio cae en una combinación muy jugada, se reparte entre más acertantes.

### 5. Optimización de la cartera

Se generan candidatos (**68 % ponderados por el modelo / 32 % uniformes**), se
construye una columna vertebral de cobertura y se optimiza con **búsqueda greedy
+ búsqueda local** maximizando una función de calidad que pondera:

| Componente | Qué mide |
| --- | --- |
| quality | calidad estadística media de las apuestas |
| numbers | números distintos cubiertos |
| pairs | pares distintos cubiertos |
| triples | tríos distintos cubiertos |
| overlap | penalización por solapamiento entre apuestas |
| balance | equilibrio de aparición de los números |
| popularity | penalización de combinaciones populares |

Cuatro estrategias ajustan esos pesos:

| Estrategia | Etiqueta | Enfoque |
| --- | --- | --- |
| `big_prize` *(por defecto)* | Máximo premio | Cobertura de pares/tríos + baja popularidad |
| `balanced` | Equilibrada | Reparte calidad estadística y cobertura |
| `coverage` | Máxima cobertura | Maximiza números, pares y tríos distintos |
| `statistical` | Estadística pura | Prioriza los números con mayor propensión |

### 6. Cobertura y claves

- **Siempre que sea posible** se buscan apuestas **disjuntas** (sin
  solapamiento). Con 10 apuestas se cubren 50 de los 54 números, y la cartera
  permite calcular probabilidades **exactas** por enumeración combinatoria.
- **Claves distintas**: con 10 apuestas se cubren los 10 dígitos, de modo que
  una apuesta lleva siempre la clave ganadora y recupera **1,50 €** de reintegro.
  Con menos apuestas se usan claves distintas priorizando las de mayor
  probabilidad histórica.

> Si no se indica `seed`, se usa una semilla determinista derivada del último
> sorteo + estrategia + número de apuestas (resultado reproducible por sorteo).
> La semilla se devuelve en la respuesta.

---

## 🧮 Probabilidades exactas de la cartera

Para una cartera de `k` apuestas **disjuntas**, el generador enumera todas las
formas de repartir los 5 números ganadores entre las apuestas (y los números no
jugados) y las 10 claves posibles. Así obtiene la distribución exacta de la
**mejor categoría** de la cartera, sin depender de aproximaciones.

Ejemplo con **10 apuestas disjuntas** (probabilidad de que la **mejor
categoría de la cartera** sea exactamente esa):

| Métrica | Valor exacto |
| --- | --- |
| 1ª categoría (5 + clave) | 1 / 3.162.510 ≈ 0,0000316 % |
| 2ª categoría (5) | 9 / 3.162.510 ≈ 0,0002846 % |
| 3ª categoría (4 + clave) | 245 / 3.162.510 ≈ 0,007747 % |
| 4ª categoría (4) | 2.205 / 3.162.510 ≈ 0,06972 % |
| 5ª categoría (3 + clave) | 11.760 / 3.162.510 ≈ 0,3719 % |
| 6ª categoría (3) | 105.840 / 3.162.510 ≈ 3,347 % |
| 7ª categoría (2 + clave) | ≈ 5,797 % |
| 8ª categoría (2) | ≈ 45,915 % |
| **Alguna de las 8 categorías** | **55,5084 %** |
| **Algún retorno** (incluye reintegro) | **100 %** |

> Las categorías 1–6 son disjuntas entre apuestas sin solapamiento (dos
> apuestas disjuntas no pueden sumar 6 aciertos entre ambas). En cambio, con 2
> aciertos sí pueden coincidir dos apuestas a la vez, por eso las categorías 7 y
> 8 se obtienen enumerando todos los repartos posibles de los 5 números
> ganadores, no multiplicando por 10. Para una sola apuesta rigen las
> probabilidades de la tabla de reglas; al añadir apuestas disjuntas aumenta la
> probabilidad de que **alguna** de ellas logre una categoría.

Además se ejecuta una **simulación Monte Carlo** (por defecto 200.000 sorteos)
sobre la cartera concreta para contrastar las probabilidades teóricas.

---

## 📡 API (backend)

Base: `/api/v1/gordo`

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
  "game": { "name": "El Gordo de la Primitiva", "max_number": 54, "ticket_price_eur": 1.5, ... },
  "seed": 123456789,
  "strategy": "big_prize",
  "strategy_label": "Máximo premio",
  "count": 10,
  "dataset": {
    "total_draws": 1123,
    "date_range": { "from": "2005-02-06", "to": "2026-10-18" },
    "next_draw": "2026-10-25"
  },
  "combinations": [
    {
      "index": 1,
      "numbers": [4, 11, 23, 31, 48],
      "key_number": 3,
      "quality": 0.87,
      "quality_grade": "alta",
      "popularity": 0.08,
      "sum": 117,
      "odd": 3, "even": 2, "low": 2, "high": 3,
      "consecutive_pairs": 0,
      "decades": [1, 1, 1, 1, 1, 0],
      "tags": ["..."],
      "theoretical": {
        "prob_1": 3.16e-8,
        "prob_2": 2.85e-7,
        "prob_3": 7.75e-6,
        "prob_4": 6.97e-5,
        "prob_5": 0.000372,
        "prob_6": 0.003347,
        "prob_7": 0.005826,
        "prob_8": 0.052432,
        "prob_2_plus": 0.062054,
        "prob_reintegro": 0.1,
        "prob_any_return": 0.155848,
        "reintegro_eur": 1.5
      }
    }
  ],
  "portfolio": {
    "tickets": 10,
    "cost_eur": 15.0,
    "coverage": { "unique_numbers": 50, "numbers_pct": 92.59, ... },
    "overlap": { "average": 0.0, "max": 0 },
    "popularity": { "risk": "bajo", "low_popularity_tickets": 9 },
    "theoretical": {
      "prob_1": 3.16e-7,
      "prob_2": 2.85e-6,
      "prob_3": 7.75e-5,
      "prob_4": 0.000697,
      "prob_5": 0.003719,
      "prob_6": 0.033467,
      "prob_7": 0.057973,
      "prob_8": 0.459148,
      "prob_any_prize": 0.555084,
      "prob_reintegro": 1.0,
      "prob_any_return": 1.0,
      "exact": true
    },
    "simulation": { "simulations": 200000, "prob_any_prize": 0.5548 },
    "keys": { "digits": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9], "distinct": 10, "guaranteed_match": true }
  },
  "analysis": { "hot_numbers": [...], "overdue_numbers": [...], "key": [...], ... },
  "recommendations": ["..."],
  "disclaimer": "..."
}
```

---

## 🖥️ Frontend

El Gordo es un "juego" de primera clase dentro de LoTor. El frontend es
multi-juego: un selector en la cabecera cambia entre El Gordo y Bonoloto y cada
juego tiene su propia navegación.

| Ruta | Página |
| --- | --- |
| `/gordo` | Generador de carteras (`pages/gordo/GordoGeneratorPage.tsx`) |
| `/gordo/statistics` | Estadísticas del histórico (`StatisticsPage.tsx`) |
| `/gordo/history` | Últimos sorteos (`HistoryPage.tsx`) |
| `/gordo/prediction` | Predicción IA legacy (enlaza al generador) |
| `/gordo/weekly-combinations` | 7 combinaciones semanales legacy |

- El generador permite elegir **número de apuestas** (1–10) y **estrategia**,
  generar una cartera nueva (semilla aleatoria) y **copiar** las combinaciones.
- Muestra: próximo sorteo, coste, cobertura (números / pares / tríos), riesgo de
  compartir premio, probabilidades por categoría y reintegro, simulación,
  análisis del histórico (calientes, fríos, retrasados, estructura, pares,
  claves) y recomendaciones.
- Los componentes de UI están en `components/gordo/` y el cliente API en
  `services/gordo.ts`.
- La lógica de formato común está en `components/shared/format.ts`.
- Consulta [`docs/FRONTEND.md`](FRONTEND.md) para la arquitectura completa del
  frontend.

---

## 🧪 Tests

```bash
cd backend
PYTHONPATH=. python -m pytest tests/test_gordo.py -q
```

Cubren: validez de las combinaciones, rangos de números y clave, apuestas
disjuntas, cobertura de claves, estrategias, reproducibilidad con semilla,
probabilidades exactas, reintegro, simulación y endpoints principales.

---

## 📐 Resumen matemático honesto

1. **No se puede predecir** una lotería uniforme; el generador no mejora la
   probabilidad por apuesta.
2. **Cobertura**: con más apuestas (y sobre todo disjuntas) aumenta la
   probabilidad de *algún* premio en categorías bajas.
3. **Anti-popularidad**: elegir combinaciones poco jugadas reduce el reparto del
   premio, que es la única vía real de mejorar el **importe esperado** de un gran
   premio.
4. **Reintegro**: cubrir las 10 claves con 10 apuestas garantiza recuperar
   1,50 €, compatible con cualquier premio de categoría.
5. **El Gordo** (5 + clave) sigue siendo **1 entre 31.625.100** por apuesta; con
   10 apuestas disjuntas la probabilidad de la 1ª categoría es 10 veces mayor
   (1 entre 3.162.510), nunca una certeza.
