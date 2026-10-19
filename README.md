# LoTor - Sistema de Predicción El Gordo de la Primitiva y Bonoloto

Sistema de predicción basado en Inteligencia Artificial para El Gordo de la Primitiva y generador inteligente de carteras para Bonoloto (España).

Proyecto de ejemplo en producción: https://lotor.tornadocore.es/

## 📋 Reglas del Juego

### El Gordo de la Primitiva

- **5 números** del 1 al 54
- **1 número clave** del 0 al 9
- Sorteo todos los domingos

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
│   │   ├── components/   # Componentes React
│   │   ├── services/     # Cliente API
│   │   ├── hooks/        # Custom hooks
│   │   └── types/        # TypeScript types
│   └── public/
└── docs/
```

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

## 📊 Fuentes de Datos

**SELAE no tiene API oficial**, pero he implementado un sistema robusto con múltiples fuentes:

1. **RSS Feed Oficial** - Canal RSS oficial de SELAE
2. **LoteriaAPI** - API gratuita de terceros
3. **Downtack API** - API con múltiples formatos
4. **Dataset CSV** - Offline-first con datos iniciales

El sistema usa **estrategia de fallback** automática: si una fuente falla, intenta la siguiente automáticamente.

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

### El Gordo de la Primitiva

- `GET /api/history` - Obtener historial de sorteos
- `POST /api/predict` - Obtener predicción para la próxima semana
- `GET /api/stats` - Estadísticas de números
- `GET /api/models` - Información sobre modelos

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
