FROM python:3.12-slim

WORKDIR /app

# Instalar dependencias del sistema y compiladores
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements del backend (versión sin PyTorch para máxima compatibilidad)
COPY backend/requirements-no-torch.txt ./requirements.txt
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Configurar variable de entorno para forzar modelos ligeros
ENV FORCE_LIGHTWEIGHT_MODELS=true
ENV ML_MODEL_TYPE=lightweight

# Copiar código de la aplicación
COPY backend/app ./app

# Copiar datos históricos (incluye el CSV expandido del Sorteo Nacional)
COPY backend/data ./data

# Verificar que los datos expandidos estén presentes
RUN ls -la /app/data/raw/ && \
    test -f /app/data/raw/nacional_historical_expanded.csv && \
    echo "✅ Nacional expanded data found" || \
    echo "⚠️ Warning: Nacional expanded data not found"

# Copiar frontend construido
COPY frontend/dist ./frontend

# Crear directorios necesarios
RUN mkdir -p data/raw data/processed app/ml/models logs

# Exponer puerto
EXPOSE 8000

# Health check - extended start period for sklearn model training (3+ minutes)
HEALTHCHECK --interval=30s --timeout=20s --start-period=180s --retries=10 \
  CMD curl -f http://localhost:8000/health || exit 1

# Comando de inicio
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
