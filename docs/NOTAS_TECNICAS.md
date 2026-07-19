# 🔧 Notas Técnicas - LoTor

## 🏗️ Arquitectura del Sistema

### Backend (FastAPI)
```
app/
├── main.py              # Entry point, configuración FastAPI
├── api/                 # Routers de API
│   ├── predictions.py   # Endpoints de predicción
│   ├── history.py       # Endpoints de historial
│   └── stats.py         # Endpoints de estadísticas
├── models/              # Pydantic models
│   └── schemas.py       # Esquemas de datos
├── services/            # Lógica de negocio
│   └── scraper.py       # Scraper de loterías
├── ml/                  # Modelos de ML
│   └── models.py        # Implementación de modelos
└── core/                # Configuración
    └── config.py        # Settings
```

### Frontend (React + Mantine)
```
src/
├── main.tsx             # Entry point
├── App.tsx              # Router principal
├── components/          # Componentes React
│   ├── Header.tsx
│   ├── HomePage.tsx
│   ├── PredictionPage.tsx
│   ├── StatisticsPage.tsx
│   └── HistoryPage.tsx
└── services/            # Cliente API
    └── api.ts
```

## 🤖 Modelos de Machine Learning

### TransformerPredictor
```python
# Arquitectura
- Embedding: números → vectores
- Positional Encoding: información de posición
- Transformer Encoder: 4 capas, 8 heads
- Prediction Head: MLP para clasificación

# Input
- Secuencia de sorteos: [n1, n2, n3, n4, n5, key] × N
- Max sequence length: 52 semanas

# Output
- Logits para números (1-54)
- Logits para número clave (0-9)
```

### LSTMPredictor
```python
# Arquitectura
- Embedding Layer
- LSTM: 2 capas, 128 hidden units
- Dropout: 0.2
- Prediction Heads: MLP separadas

# Ventajas
- Eficiente para secuencias
- Menor complejidad que Transformer
- Buen baseline
```

### EnsemblePredictor
```python
# Estrategia
- Combina N modelos
- Promedia probabilidades
- Selecciona top-K números
- Genera alternativas con ruido

# Beneficios
- Reduce overfitting
- Mejora generalización
- Más robusto
```

## 📊 Pipeline de Datos

### 1. Scraping
```python
PrimitivaScraper
├── fetch_recent_draws(count=52)
├── fetch_draw_by_date(date)
└── save_to_csv(filepath)
```

### 2. Procesamiento
```python
HistoricalDataManager
├── get_historical_data()
├── get_processed_data()
└── _process_draws_for_ml()
```

### 3. Feature Engineering
```python
# Features calculadas
- Sum, mean, std de números
- Min, max, range
- Day of week, month, year
- Week number
```

## 🔢 Algoritmos de Predicción

### Selección de Números
```python
def _select_top_numbers(probs):
    # 1. Ajustar índices (0-53 → 1-54)
    # 2. Evitar repeticiones
    # 3. Seleccionar top-5
    # 4. Validar rango [1, 54]
```

### Número Clave
```python
# Basado en:
- Probabilidades del modelo
- Frecuencia histórica
- Patrones temporales
```

## 🎨 Frontend Architecture

### State Management
- React hooks (useState, useEffect)
- Custom hooks para API calls
- No Redux (simplicidad)

### API Client
```typescript
// Axios instance with interceptors
const api = axios.create({
  baseURL: '/api/v1',
  headers: { 'Content-Type': 'application/json' }
})
```

### Component Structure
```
Header
├── Navigation
└── Responsive menu

Pages
├── HomePage: Landing, features
├── PredictionPage: ML predictions
├── StatisticsPage: Data viz
└── HistoryPage: Historical draws
```

## 🚀 Deployment

### Docker
```yaml
# docker-compose.yml
services:
  - backend: FastAPI + PyTorch
  - frontend: Nginx + React build
```

### Environment Variables
```bash
# Backend
HOST=0.0.0.0
PORT=8000
DEBUG=False
MAX_HISTORY_LENGTH=52

# Frontend
VITE_API_URL=http://localhost:8000
```

## 📈 Performance

### Optimizaciones
- **Lazy loading** de modelos
- **Caching** de datos históricos
- **Pagination** de resultados
- **Debouncing** de requests

### Scalability
- **Horizontal**: Multiple backend instances
- **Vertical**: GPU acceleration for ML
- **Cache**: Redis for frequent queries

## 🔍 Debugging

### Backend
```bash
# Logs
tail -f logs/app.log

# Debug mode
DEBUG=True uvicorn app.main:app --reload

# Model inspection
curl /api/v1/predictions/models/status
```

### Frontend
```bash
# Dev tools
npm run dev

# Build analysis
npm run build -- --analyze

# Type checking
npx tsc --noEmit
```

## 🧪 Testing

### Backend Tests
```python
# pytest structure
tests/
├── test_api/
├── test_models/
└── test_services/
```

### Frontend Tests
```typescript
// Jest + React Testing Library
import { render, screen } from '@testing-library/react'
```

## 🔒 Seguridad

### Backend
- CORS configurado
- Rate limiting recomendado
- Input validation (Pydantic)
- SQL injection prevention (ORM)

### Frontend
- HTTPS en producción
- Content Security Policy
- XSS protection (React)
- No sensitive data in client

## 📝 Mejoras Futuras

### Short-term
- [ ] Testing suite completo
- [ ] Monitoring con Sentry/Grafana
- [ ] Rate limiting
- [ ] WebSocket para tiempo real

### Long-term
- [ ] más modelos (XGBoost, Random Forest)
- [ ] AutoML para hiperparámetros
- [ ] Análisis de sentimiento
- [ ] Telegram/Discord bot
- [ ] Mobile app (React Native)

---

**Documentación actualizada: 2026-07-16**
