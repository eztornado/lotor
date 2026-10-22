# ⚽ La Quiniela — Modelo estadístico y optimizador de boletos

Módulo de LoTor que estima probabilidades **1 / X / 2** para los 15 partidos de
La Quiniela y construye boletos optimizados: un **múltiple** con dobles y
triples o una **cartera de columnas simples**. Está disponible en el backend
(`/api/v1/quiniela`) y en el frontend (`/quiniela`).

> ⚠️ **Aviso**: La Quiniela es un juego de azar. El modelo estima
> probabilidades a partir del histórico; no predice resultados ni garantiza
> premios. Los premios son de reparto (*pari-mutuel*): dependen de cuántos
> acertantes haya en cada jornada. Juega solo dinero que puedas permitirte
> perder.

---

## 📋 Reglas del juego

| Regla | Valor |
| --- | --- |
| Partidos con signo | 14 |
| Signos posibles | 1 (local), X (empate), 2 (visitante) |
| Pleno al 15 | Marcador exacto del partido 15 |
| Precio por columna | 0,75 € |
| Múltiples | Hasta 7 dobles y 4 triples (según configuración) |
| Categorías | 15, 14, 13, 12, 11 y 10 aciertos |

Una **columna** contiene un signo por cada uno de los 14 partidos y un marcador
para el pleno. Un **doble** marca dos signos en un partido; un **triple**, los
tres. El número de columnas de un múltiple es el producto de los signos
marcados:

```
columnas = ∏ |S_i|        coste = columnas × 0,75 €
```

Ejemplos: 3 dobles → 8 columnas (6,00 €); 1 triple + 2 dobles → 12 columnas
(9,00 €); 2 triples + 2 dobles → 36 columnas (27,00 €).

---

## 🗂️ Datos

| Fichero | Contenido |
| --- | --- |
| `backend/data/raw/quiniela_matches.csv` | 20.781 partidos (2014-08-23 → 2026-10-21) |
| `backend/data/raw/quiniela_fixtures.csv` | Jornadas 17–19 de 2026/27 (45 partidos) |

- **Resultados históricos**: [Football-Data.co.uk](https://www.football-data.co.uk/)
  (`SP1`, `SP2`, `E0`, `D1`, `I1`, `F1`, `N1`, `P1`). Incluye cuotas medias
  cuando están disponibles.
- **Calendario**: página pública de
  [Eduardo Losilla](https://www.eduardolosilla.es/quiniela/ayudas/proximas).
- **Importador reproducible**: `python backend/scripts/import_quiniela.py`
  (admite `--offline`).
- **Actualización**: `GET|POST /api/v1/quiniela/refresh?scope=fixtures|matches|all`.

### Normalización de equipos

Las fuentes usan abreviaturas distintas (`R.MADRID`, `Real Madrid`,
`R MADRID`, `AT.MADRID`, `ATH.CLUB`). `quiniela_data.py` normaliza mayúsculas,
acentos, puntuación y sufijos societarios, aplica un diccionario de alias
idempotente y, como último recurso, una búsqueda difusa conservadora
(≥ 0,86 de similitud). Los equipos sin histórico —divisiones inferiores, Liga F,
rivales europeos— se detectan explícitamente.

Cada partido lleva su competición inferida (`LaLiga`, `LaLiga Hypermotion`,
`Copa del Rey`, `Europea`, `Liga F`). Una jornada puede mezclar competiciones;
en ese caso `competition` vale `Mixta` y `competitions` enumera las presentes.

---

## 🧠 Modelo

### 1. Poisson Dixon-Coles con pesos temporales

Para cada partido se estiman los goles esperados:

```
λ_local = exp(μ_liga + ventaja_campo + ataque_local − defensa_visitante + Δ)
λ_visitante = exp(μ_liga + ataque_visitante − defensa_local − Δ)
```

- `μ_liga`: nivel medio de goles de la competición.
- `ataque` / `defensa`: fuerza ofensiva y defensiva de cada equipo.
- `Δ`: diferencia de nivel entre ligas (Copa, competiciones europeas).
- Pesos temporales: cada partido pesa `0,5^(días / vida_media)`, con una vida
  media de **420 días** (~14 meses).
- Regularización L2 para que los equipos con pocos datos se contraigan hacia
  la media.
- Optimización con Adam (260 épocas, learning rate 0,045).

La matriz de marcadores 0–8 goles por equipo incorpora la **corrección
Dixon-Coles** en los resultados bajos (`ρ = −0,08`), que ajusta la
sobreestimación de empates 0-0 y 1-1 del Poisson independiente.

### 2. Elo con diferencia de goles

Un Elo incremental (K = 20, ventaja de campo = 65 puntos) se ajusta sobre los
últimos años. El multiplicador por diferencia de goles penaliza más las
derrotas amplias. El Elo se convierte en una segunda matriz de marcadores y se
mezcla con Poisson:

```
peso_poisson = 0,35 + 0,45 × datos
```

donde `datos` mide cuántos partidos recientes tiene el equipo. Así, cuando hay
histórico se confía más en Poisson; cuando no, en el prior de competición.

### 3. Priors de liga y competición

Para equipos sin histórico se usa el nivel de su liga y una confianza
explícitamente baja:

| Competición | Offset (log-goles) |
| --- | --- |
| LaLiga | +0,20 |
| LaLiga Hypermotion | 0,00 |
| Premier League | +0,25 |
| Bundesliga | +0,20 |
| Serie A | +0,18 |
| Ligue 1 | +0,15 |
| Eredivisie | +0,06 |
| Primeira Liga | +0,05 |
| Divisiones inferiores | −0,55 |
| Competición europea | +0,10 |

En Copa, un equipo de Tercera recibe el offset de divisiones inferiores; en
Europa, el de competición europea. La interfaz muestra `data_quality` y
`confidence` para que el usuario sepa cuándo el modelo tiene poca información.

### 4. Pleno al 15

El pleno se estima con el marcador más probable de la matriz Dixon-Coles del
partido 15. La respuesta incluye las cinco alternativas más probables. El
acierto del pleno se trata como un suceso Bernoulli independiente de los 14
signos.

### 5. Backtest

`GET /api/v1/quiniela/backtest?limit=400` entrena con los partidos anteriores a
un corte (82 % del histórico) y evalúa sobre los posteriores:

- **Accuracy** y comparación con el baseline (siempre local).
- **Log-loss** y **Brier score**.
- **Calibración** por tramos de confianza.

Con los datos actuales el modelo ronda **56 % de acierto** frente al **45 %**
del baseline, con log-loss ≈ 0,97 frente a 1,06 y Brier ≈ 0,58. Es una mejora
modesta pero consistente: el fútbol tiene mucha incertidumbre irreducible.

---

## 🎯 Optimización del boleto

### Distribución exacta de aciertos

Para un boleto con conjuntos de signos `S_i`, la probabilidad de acertar el
partido `i` es:

```
c_i = Σ P(resultado) para resultado ∈ S_i
```

Bajo el modelo los partidos son independientes, así que el número de aciertos
sigue una **Poisson-binomial**:

```
P(k aciertos) = coeficiente de ∏ (1 − c_i + c_i·z)
```

Se calcula con programación dinámica en `O(14²)`, sin simulaciones. Para el
total de 15 se convoluciona con el Bernoulli del pleno.

### Múltiple

El optimizador parte de la columna más probable y va añadiendo signos
(dobles/triples) en los partidos donde más mejora la utilidad, respetando:

- presupuesto (el límite real de gasto),
- máximo de dobles y triples,
- máximo de columnas, que se deriva del presupuesto (0,75 € por columna).

La respuesta incluye `budget.max_columns` y `budget.max_cost` para que la
interfaz pueda explicar cuánto puede gastar realmente el múltiple. Los dobles y
triples disponibles pueden dejar el coste por debajo del presupuesto: no se
rellena con columnas sin valor estadístico.

La utilidad pondera las probabilidades de 10–15 aciertos y añade un pequeño
término de aciertos esperados. Después se ejecuta una búsqueda local que
intercambia un signo de un partido por otro de otro partido.

Con un solo boleto múltiple, cualquier objetivo creciente en el número de
aciertos conduce al mismo óptimo: cubrir los partidos más inciertos hasta
agotar presupuesto y límites. Por eso el modo múltiple usa siempre el objetivo
equilibrado y la interfaz no ofrece estrategias; éstas se reservan para la
cartera de columnas simples, donde sí cambian qué columnas se eligen.

### Predicción IA (máximo premio)

La sección **Predicción IA** no reutiliza el objetivo equilibrado: maximiza
exactamente la probabilidad del premio alto. Bajo independencia,

```
P(15) = P(acertar los 14 partidos) × P(marcador del pleno)
      = (∏ c_i) × p_pleno
```

Como `p_pleno` depende solo del marcador elegido y no de los signos, el
optimizador maximiza `Σ log(c_i)` con búsqueda greedy y búsqueda local sobre
los límites de presupuesto, dobles y triples. El pleno se fija en el marcador
más probable del modelo. Es un objetivo distinto al del generador: aquí no se
premia la cobertura de 10-12 aciertos, sino la probabilidad de acertar los 14
partidos y el pleno.

La respuesta incluye la probabilidad exacta de 15, 14 y al menos 13, el
retorno estimado, variantes forzando el segundo signo en los partidos más
abiertos y una explicación legible. Esa explicación se construye de forma
determinista a partir del modelo y del histórico. No se llama a un LLM
generativo: un modelo de lenguaje no mejora la calibración de las
probabilidades y sí añadiría opacidad y dependencia externa.

### Cartera de columnas simples

Para varias columnas simples se generan candidatos deterministas, variantes de
segundo signo y muestras con distintas temperaturas. Con **Monte Carlo** se
simulan resultados compartidos y se selecciona greedy la cartera que maximiza
la probabilidad de que **el mejor boleto** alcance premio. La distribución del
máximo no es la de una sola columna: las columnas comparten el mismo sorteo y
sus aciertos están correlacionados. La selección y la evaluación usan semillas
distintas para que las métricas reportadas no sean in-sample.

---

## 📡 API

Base: `/api/v1/quiniela`

| Método | Ruta | Descripción |
| --- | --- | --- |
| `GET` | `/meta` | Reglas, dataset, estrategias y próxima jornada |
| `GET` | `/jornadas` | Jornadas del calendario local |
| `GET` | `/jornada?jornada=17` | Predicciones 1-X-2 y pleno |
| `GET` | `/jornada/{n}` | Alias con el número en la ruta |
| `GET` | `/prediction` | Boleto con mayor probabilidad de pleno al 15 |
| `GET` | `/stats` | Dataset, modelo, ligas, equipos y backtest |
| `GET` | `/backtest?limit=400` | Backtest fuera de muestra |
| `GET` | `/history?limit=50` | Últimos partidos |
| `GET` | `/teams/{name}` | Perfil de un equipo |
| `POST` | `/generate` | Genera múltiple o cartera simple |
| `GET` | `/generate?...` | Alias GET |
| `GET/POST` | `/refresh?scope=all` | Actualiza calendario/resultados |

### Petición de generación

```json
{
  "jornada": 17,
  "mode": "multiple",
  "budget": 20,
  "max_doubles": 4,
  "max_triples": 2,
  "count": 5,
  "strategy": "balanced",
  "seed": 123456789
}
```

- `mode`: `multiple` (un boleto con dobles/triples) o `simple` (varias
  columnas).
- `budget`: presupuesto máximo en euros (mínimo 0,75).
- `max_doubles` / `max_triples`: límites del múltiple.
- `count`: columnas simples (1–10); se recorta si el presupuesto no llega.
- `strategy`: `balanced` | `coverage` | `max_probability` | `jackpot`. En
  `multiple` se normaliza a `balanced`, porque el óptimo del boleto único no
  depende de la estrategia.
- `seed`: opcional; se devuelve para reproducir el resultado.

`GET /prediction` acepta `jornada`, `season`, `budget`, `max_doubles`,
`max_triples` y `seed`, y devuelve la combinación principal, alternativas,
`target` con las probabilidades 15/14/≥13, el bloque `model` con backtest y
`reasoning` con la explicación.

### Respuesta (resumen)

```jsonc
{
  "jornada": {
    "jornada": 17,
    "season": "2026/27",
    "competition": "Mixta",
    "competitions": ["Copa del Rey", "LaLiga Hypermotion"],
    ...
  },
  "matches": [
    {
      "match_number": 1,
      "home_team": "RSD.ALCALA",
      "away_team": "LAS PALMAS",
      "probabilities": { "1": 0.249, "X": 0.267, "2": 0.484 },
      "expected_goals": { "home": 0.87, "away": 1.60 },
      "most_likely_score": "0-1",
      "confidence": 0.39,
      "data_quality": "baja",
      "pick": "2"
    }
  ],
  "tickets": [
    {
      "index": 1,
      "signs": [{ "match_number": 1, "signs": ["2"], "coverage": 0.484 }, ...],
      "pleno": { "score": "0-2", "probability": 0.1279 },
      "columns": 24,
      "cost": 18.0,
      "doubles": 3,
      "triples": 1,
      "expected_hits": 7.9,
      "expected_total_hits": 8.028,
      "guaranteed_hits": 1,
      "category_probabilities": { "10": 0.1236, "11": 0.0577, ... },
      "expanded_columns": [...]
    }
  ],
  "portfolio": {
    "columns": 24,
    "cost": 18.0,
    "expected_best_hits": 7.9,
    "expected_total_hits": 8.028,
    "category_probabilities": { "10": 0.1236, ... },
    "prize_estimate": {
      "probability_any_prize": 0.2047,
      "expected_return": { "low": 3.26, "average": 10.62, "high": 44.27 },
      "roi": { "low": -0.819, "average": -0.410, "high": 1.46 },
      "note": "Estimación conservadora con premios medios orientativos..."
    },
    "method": "exact_poisson_binomial"
  },
  "analysis": { "most_confident": [...], "pleno": {...}, "data_quality": {...} },
  "recommendations": ["..."],
  "disclaimer": "..."
}
```

> Los importes de premio son **estimaciones orientativas** con premios medios.
> La Quiniela reparte el boleto según los acertantes; el retorno real puede
> variar mucho. La interfaz muestra un rango bajo/medio/alto y advierte cuando
> la estimación media sale favorable.
>
> El retorno esperado es **conservador**: suma solo el mejor boleto de la
> cartera. Un múltiple puede cobrar varias categorías a la vez y una cartera
> simple puede tener varias columnas premiadas; por eso el retorno real puede
> ser mayor, pero nunca está garantizado. La probabilidad de premio sí es
> exacta para el múltiple (Poisson-binomial) y Monte Carlo para la cartera.

---

## 🖥️ Frontend

| Ruta | Página |
| --- | --- |
| `/quiniela` | Generador (`pages/quiniela/QuinielaPage.tsx`) |
| `/quiniela/prediccion` | Predicción IA: máxima probabilidad de pleno al 15 |
| `/quiniela/estadisticas` | Modelo, ligas, equipos y backtest |
| `/quiniela/historial` | Últimos partidos con filtros |

El generador permite:

- elegir jornada, modo, presupuesto y, en columnas simples, estrategia;
- limitar dobles/triples o fijar el número de columnas simples;
- ver el boleto completo con cobertura, marcador probable y pleno;
- expandir las columnas del múltiple;
- consultar la distribución de aciertos, la probabilidad de premio y el
  retorno estimado;
- copiar el boleto en texto.

Componentes en `frontend/src/components/quiniela/` y cliente API en
`frontend/src/services/quiniela.ts`.

---

## 🧪 Tests

```bash
cd backend
PYTHONPATH=. python -m pytest tests/test_quiniela.py -q
```

Cubren:

- validez del dataset y de las jornadas,
- probabilidades normalizadas y marcadores,
- resolución de equipos conocidos y desconocidos,
- Poisson-binomial exacta,
- coste y expansión de múltiples,
- presupuesto, dobles/triples y recorte de columnas,
- objetivo P(15), alternativas y explicación de la predicción IA,
- reproducibilidad con semilla,
- endpoints principales y errores de validación.

---

## 📐 Resumen matemático honesto

1. **El fútbol no es determinista.** El modelo produce probabilidades
   calibradas, no certezas. Un 55 % de acierto en el signo más probable es un
   resultado realista y útil, no una garantía.
2. **Los dobles y triples no mejoran la probabilidad por columna**; compran
   cobertura. Un múltiple de 24 columnas cuesta 24 veces más y cubre más
   resultados, pero el retorno esperado por euro no aumenta por arte de magia.
3. **La ventaja real** está en (a) estimar mejor que el azar qué partidos son
   más probables, (b) concentrar los dobles en los partidos más inciertos y
   (c) no sobrepagar columnas que no aportan cobertura.
4. **Los premios son de reparto.** Dos boletos con los mismos aciertos cobran
   lo mismo, pero un premio muy jugado se reparte entre más personas.
5. **Juega con responsabilidad.** La casa siempre tiene ventaja; ningún sistema
   cambia eso.
