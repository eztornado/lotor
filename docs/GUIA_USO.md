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

### Predicción IA

1. Navega a `/prediction`
2. El sistema genera automáticamente una predicción usando:
   - **Transformer**: Modelos de attention para secuencias
   - **LSTM**: Redes recurrentes para patrones temporales
   - **Statistical**: Análisis de frecuencias históricas
3. Puedes ver:
   - Números predichos (5 del 1-54)
   - Número clave (0-9)
   - Confianza del modelo
   - Combinaciones alternativas

### Estadísticas

1. Navega a `/statistics`
2. Visualiza:
   - Números calientes (alta frecuencia)
   - Números fríos (baja frecuencia)
   - Distribución de números clave
   - Patrones históricos

### Historial

1. Navega a `/history`
2. Revisa los últimos 52 sorteos
3. Puedes actualizar los datos manualmente

## 🐳 Docker

```bash
# Construir y ejecutar
docker-compose up --build

# Solo backend
docker-compose up backend

# Solo frontend
docker-compose up frontend
```

## 🔧 API Endpoints

### Predicciones
- `POST /api/v1/predictions/predict` - Predicción completa (ensemble)
- `POST /api/v1/predictions/predict/statistical` - Predicción estadística
- `GET /api/v1/predictions/models/status` - Estado de modelos

### Historial
- `GET /api/v1/history/recent` - Últimos sorteos
- `GET /api/v1/history/date/{date}` - Sorteo específico
- `GET /api/v1/history/range` - Rango de fechas
- `GET /api/v1/history/refresh` - Actualizar datos

### Estadísticas
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
