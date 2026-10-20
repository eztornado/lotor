# 🎱 LoTor - Guía de Uso

## 🚀 Inicio Rápido

### 1. Clonar e Instalar

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Frontend
cd ../frontend
npm install
```

### 2. Configuración

```bash
# Backend
cp backend/.env.example backend/.env
# Editar backend/.env si es necesario

# Frontend
# No requiere configuración adicional
```

### 3. Ejecutar

```bash
# Backend (terminal 1)
cd backend
uvicorn app.main:app --reload

# Frontend (terminal 2)
cd frontend
npm run dev
```

### 4. Acceder

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

## 📊 Uso de la Aplicación

La app es **multi‑juego**: el selector de la cabecera cambia entre El Gordo y
Bonoloto. Cada juego tiene su propia navegación.

### El Gordo de la Primitiva

1. **Generador** (`/gordo`): elige entre 1 y 10 apuestas y una estrategia
   (`big_prize`, `balanced`, `coverage`, `statistical`). Muestra el coste, la
   cobertura, el riesgo de compartir premio, las probabilidades exactas de las
   8 categorías, el reintegro, la simulación y recomendaciones.
2. **Estadísticas** (`/gordo/statistics`): números frecuentes, calientes, fríos,
   retrasados, pares y distribución de claves sobre los 1.123 sorteos desde
   2005.
3. **Historial** (`/gordo/history`): últimos sorteos con la fuente del dato y
   botón de actualización.
4. **Predicción IA** (`/gordo/prediction`): página legacy que enlaza al nuevo
   generador.

### Bonoloto

1. **Generador** (`/bonoloto`): de 1 a 10 apuestas con estrategia, cobertura,
   reintegros, probabilidades y análisis.
2. **Estadísticas** (`/bonoloto/estadisticas`) e **historial**
   (`/bonoloto/historial`).

### Rutas legacy

Las rutas antiguas (`/prediction`, `/statistics`, `/history`,
`/weekly-combinations`) redirigen a sus equivalentes bajo `/gordo`.

## 🐳 Docker

El repositorio incluye un `Dockerfile` en la raíz que construye el frontend y lo
sirve con FastAPI en el puerto **8000**:

```bash
docker build -t lotor .
docker run -p 8000:8000 lotor
```

También existe `docker-compose.yml` para desarrollo. En producción (Coolify) se
usa el `Dockerfile` raíz con `backend/requirements-no-torch.txt`; no es
necesario instalar PyTorch.

## 🔧 API Endpoints

### Generador de El Gordo (`/api/v1/gordo`)
- `GET /meta` - Reglas, dataset y estrategias
- `GET /next-draw` - Próximo sorteo (domingos)
- `GET /history?limit=50` - Últimos sorteos
- `GET /stats` - Estadísticas, claves y probabilidades
- `POST /generate` / `GET /generate` - Cartera de 1 a 10 apuestas
- `GET|POST /refresh` - Actualizar histórico desde Lotoideas/SELAE

### Generador de Bonoloto (`/api/v1/bonoloto`)
- `GET /meta`, `GET /next-draw`, `GET /history`, `GET /stats`
- `POST /generate` / `GET /generate` - Cartera de 1 a 10 apuestas
- `GET|POST /refresh` - Actualizar histórico

### Predicción IA legacy
- `POST /api/v1/predictions/predict` - Predicción completa (ensemble)
- `POST /api/v1/predictions/predict/statistical` - Predicción estadística
- `GET /api/v1/predictions/models/status` - Estado de modelos
- `GET /api/v1/history/recent` - Últimos sorteos
- `GET /api/v1/history/date/{date}` - Sorteo específico
- `GET /api/v1/history/range` - Rango de fechas
- `GET /api/v1/history/refresh` - Actualizar datos
- `GET /api/v1/stats/general` - Estadísticas generales
- `GET /api/v1/stats/number/{num}` - Estadísticas de número
- `GET /api/v1/stats/patterns` - Análisis de patrones

## 🎯 Arquitectura de Modelos

### 1. TransformerPredictor
- Usa mecanismos de attention
- Captura dependencias complejas
- Ideal para secuencias largas

### 2. LSTMPredictor
- Redes recurrentes
- Aprende patrones secuenciales
- Eficiente para series temporales

### 3. EnsemblePredictor
- Combina múltiples modelos
- Promedia predicciones
- Aumenta robustez

### 4. StatisticalPredictor
- Análisis de frecuencias
- Números calientes/fríos
- Basado en probabilidades

## ⚙️ Configuración Avanzada

### Backend (.env)
- `MAX_HISTORY_LENGTH`: Semanas de historial (default: 52)
- `CACHE_TTL`: Tiempo de cache en segundos (default: 3600)
- `DEBUG`: Modo debug (default: True)

### Modelos
- Ubicación: `backend/app/ml/models/`
- Puedes agregar nuevos modelos en `app/ml/models.py`

## 📈 Monitoreo

```bash
# Ver logs del backend
tail -f backend/logs/app.log

# Ver modelos cargados
curl http://localhost:8000/api/v1/predictions/models/status
```

## 🚨 Solución de Problemas

### Backend no inicia
```bash
# Verificar puerto 8000
lsof -i :8000

# Reinstalar dependencias
pip install --force-reinstall -r requirements.txt
```

### Frontend no conecta
```bash
# Verificar puerto 3000
lsof -i :3000

# Limpiar cache npm
npm cache clean --force
rm -rf node_modules
npm install
```

### Datos no se actualizan
```bash
# Forzar refresh
curl http://localhost:8000/api/v1/history/refresh

# Verificar archivos de datos
ls backend/data/raw/
```

## 📚 Recursos Adicionales

- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [Mantine UI](https://mantine.dev/)
- [PyTorch](https://pytorch.org/)
- [React](https://react.dev/)

---

**Recuerda**: Este sistema es solo para fines educativos y entretenimiento. La lotería es un juego de azar.
