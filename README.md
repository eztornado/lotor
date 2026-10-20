# LoTor - Sistema de Predicción El Gordo de la Primitiva y Bonoloto

Sistema de predicción basado en Inteligencia Artificial para El Gordo de la
Primitiva y generadores inteligentes de carteras para El Gordo y Bonoloto
(España).

Proyecto de ejemplo en producción: https://lotor.tornadocore.es/

## 📋 Reglas del Juego

### El Gordo de la Primitiva

- **5 números** del 1 al 54
- **1 número clave** del 0 al 9
- **8 categorías de premio** (de 5 + clave a 2 aciertos) + **reintegro** de
  1,50 € si coincide la clave, compatible con cualquier categoría
- Sorteo todos los domingos · apuesta de **1,50 €**
- Generador de carteras de **1 a 10 apuestas** con histórico desde 2005,
  probabilidades exactas, cobertura de claves y análisis anti-popularidad

[Ver documentación completa de El Gordo](docs/GORDO.md)

### Bonoloto

- **6 números** del 1 al 49 + **complementario** + **reintegro** (0–9)
- Sorteo de **lunes a sábado**
- Generador de carteras de **1 a 10 apuestas** con histórico desde 1988

[Ver documentación completa de Bonoloto](docs/BONOLOTO.md)

## 🏗️ Arquitectura

### Stack Tecnológico

- **Backend**: FastAPI (Python 3.12+)
- **Frontend**: React + Mantine UI
- **Machine Learning**: 
  - PyTorch para modelos deep learning
  - Transformers para series temporales
  - Scikit-learn para modelos clásicos
  - XGBoost para gradient boosting
- **Database**: SQLite + Pandas para análisis
- **APIs**: Loterías y Apuestas del Estado (scraping)

### Estructura del Proyecto

```
LoTor/
├── backend/
│   ├── app/
│   │   ├── api/          # Endpoints FastAPI
│   │   ├── models/       # Modelos de datos
│   │   ├── services/     # Lógica de negocio
│   │   ├── core/         # Configuración
│   │   └── ml/           # Modelos de ML
│   └── data/
│       ├── raw/          # Datos históricos sin procesar
│       └── processed/    # Datos procesados para ML
├── frontend/
│   ├── src/
│   │   ├── components/   # Componentes UI (layout + por juego)
│   │   ├── pages/        # Páginas (home, gordo/, bonoloto/)
│   │   ├── services/     # Cliente API (client, gordo, bonoloto)
│   │   ├── games.ts      # Registro multi-juego (navegación/colores)
│   │   └── App.tsx       # Router y layout
│   └── public/
└── docs/
```

La app es **multi-juego** (El Gordo y Bonoloto) con un selector en la cabecera.
Ver [documentación del frontend](docs/FRONTEND.md).

## 🚀 Instalación

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

## 🐳 Despliegue (Docker / Coolify)

El repositorio incluye un **`Dockerfile` en la raíz** pensado para Coolify y para
cualquier build de un solo contenedor:

1. **Etapa frontend**: `node:20-alpine` ejecuta `npm ci` + `npm run build`.
2. **Etapa backend**: `python:3.12-slim` instala
   [`backend/requirements-no-torch.txt`](backend/requirements-no-torch.txt)
   (sin PyTorch; usa modelos ligeros/estadísticos).
3. Copia el `dist` del frontend y FastAPI lo sirve en `http://localhost:8000`
   (`/` y rutas SPA), con la API bajo `/api/v1`.

```bash
# Build manual
docker build -t lotor .
docker run -p 8000:8000 lotor
```

En **Coolify**: Build Pack = `Dockerfile`, Base Directory = `/`, Dockerfile
Location = `/Dockerfile`, puerto expuesto `8000`.

> La app funciona sin PyTorch: `torch` solo se usa si está instalado; si no, el
> `ModelLoader` cae automáticamente en `lightweight_models` (scikit-learn) o en
> el modelo estadístico.

## 📊 Fuentes de Datos

**SELAE no tiene una API histórica oficial**, así que los generadores usan
datasets CSV completos y un importador reproducible desde las hojas públicas de
Lotoideas (resultados oficiales de SELAE):

- **El Gordo**: `backend/data/raw/gordo_historical.csv`, 1.123 sorteos desde el
  06/02/2005 (formato 5 números + clave).
- **Bonoloto**: `backend/data/raw/bonoloto_historical.csv`, 9.420 sorteos desde
  el 28/02/1988.
- Scripts: `backend/scripts/import_gordo.py` e
  `backend/scripts/import_bonoloto.py` (con modo `--offline`).
- API de actualización: `GET|POST /api/v1/gordo/refresh` y
  `/api/v1/bonoloto/refresh`.

Los datasets se cachean en memoria y son la fuente de verdad de los
generadores. Los endpoints legacy de predicción conservan sus fuentes con
fallback.

[Ver documentación completa de fuentes de datos](docs/DATASETS.md)

## 📊 Modelos de ML

### 1. Transformer para Series Tempinales
- Usa attention mechanisms para capturar patrones temporales
- Procesa secuencias de sorteos anteriores

### 2. LSTM/GRU
- Redes recurrentes para aprendizaje de patrones secuenciales

### 3. XGBoost
- Gradient boosting para clasificación multiclase

### 4. Análisis Estadístico
- Frecuencia de números
- Análisis de calor/frío
- Patrones de números consecutivos

## 📡 API Endpoints

### El Gordo de la Primitiva (`/api/v1/gordo`)

- `GET /meta` - Reglas, estado del dataset y estrategias
- `GET /next-draw` - Fecha del próximo sorteo
- `GET /history?limit=50` - Últimos sorteos
- `GET /stats` - Estadísticas, claves y probabilidades
- `POST /generate` / `GET /generate` - Genera de 1 a 10 combinaciones con
  estrategia `big_prize`, `balanced`, `coverage` o `statistical`
- `GET|POST /refresh` - Actualiza el histórico (Lotoideas/SELAE)

> El primer premio (5 + clave) es siempre **1 entre 31.625.100** por apuesta.
> Con 10 apuestas disjuntas y las 10 claves cubiertas, la probabilidad de alguna
> de las 8 categorías es **55,5084 %** y el reintegro de 1,50 € está garantizado
> en una de las apuestas. El generador optimiza cobertura y evita combinaciones
> populares; no predice el azar.

Los endpoints legacy de predicción IA (`/api/v1/predictions`, `/api/v1/history`,
`/api/v1/stats`) siguen disponibles para la página de predicción.

### Bonoloto (`/api/v1/bonoloto`)

- `GET /meta` - Reglas, estado del dataset y estrategias
- `GET /next-draw` - Fecha del próximo sorteo
- `GET /history?limit=50` - Últimos sorteos
- `GET /stats` - Estadísticas y probabilidades
- `POST /generate` / `GET /generate` - Genera de 1 a 10 combinaciones
- `GET|POST /refresh` - Actualiza el histórico (Lotoideas/SELAE)

> La probabilidad del <em>jackpot</em> por apuesta es siempre <strong>1 entre 13.983.816</strong>.
> El generador optimiza cobertura y evita combinaciones populares (menor reparto); no predice el azar.

## ⚠️ Descargo de Responsabilidad

Este sistema es solo para fines educativos y de entretenimiento. La lotería es un juego de azar y ningún sistema de predicción puede garantizar resultados. Juega de forma responsable.

## 📄 Licencia

MIT License - Ver LICENSE para más detalles

---

**Sources**:
- [Comprar al Gordo de la Primitiva - Jugar al Gordo Online](https://tulotero.es/jugar-gordo-primitiva/)
- [Loteria API: API Loterías España Gratis (JSON)](https://loteriasapi.com/)
- [Lotoideas - Primitiva Resultados Históricos](https://www.lotoideas.com/primitiva-resultados-historicos-de-todos-los-sorteos/)
