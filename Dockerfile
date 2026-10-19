# Imagen única de producción:
#   - Etapa 1: compila el frontend (Vite)
#   - Etapa 2: backend FastAPI sin PyTorch, sirviendo el frontend compilado
#
# Coolify construye este Dockerfile desde la raíz del repositorio.

# -------------------------
# Etapa 1: build del frontend
# -------------------------
FROM node:20-alpine AS frontend-build

WORKDIR /frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

# -------------------------
# Etapa 2: backend + estáticos
# -------------------------
FROM python:3.12-slim

WORKDIR /app

# Dependencias del sistema
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Dependencias Python (sin PyTorch)
COPY backend/requirements-no-torch.txt ./requirements.txt
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Código y datos del backend
COPY backend/app ./app
COPY backend/data ./data

# Frontend compilado en la etapa anterior
COPY --from=frontend-build /frontend/dist ./frontend

# Forzar modelos ligeros (no hay torch en la imagen)
ENV FORCE_LIGHTWEIGHT_MODELS=true
ENV ML_MODEL_TYPE=lightweight

# Directorios necesarios
RUN mkdir -p data/raw data/processed app/ml/models logs

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=20s --start-period=60s --retries=5 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
