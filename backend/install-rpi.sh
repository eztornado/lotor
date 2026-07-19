#!/bin/bash
# Script de instalación optimizado para Raspberry Pi (ARM)

echo "🎯 Instalando LoTor Backend para Raspberry Pi 3"

# Actualizar sistema
echo "📦 Actualizando sistema..."
sudo apt-get update && sudo apt-get upgrade -y

# Instalar dependencias del sistema
echo "🔧 Instalando dependencias del sistema..."
sudo apt-get install -y \
    python3-dev \
    python3-pip \
    python3-venv \
    build-essential \
    git \
    libatlas-base-dev \
    libopenblas-dev \
    libffi-dev \
    libssl-dev

# Crear entorno virtual
echo "🐍 Creando entorno virtual..."
python3 -m venv venv
source venv/bin/activate

# Actualizar pip
echo "📦 Actualizando pip..."
pip install --upgrade pip setuptools wheel

# Instalar PyTorch específico para ARM (primero, porque es el más complicado)
echo "🔥 Instalando PyTorch para ARM..."
pip install torch --extra-index-url https://www.piwheels.org/simple

# Si falla PyTorch, instalar versión alternativa
if ! pip show torch > /dev/null; then
    echo "⚠️ PyTorch falló, instalando versión CPU-only..."
    pip install torch --index-url https://download.pytorch.org/whl/cpu
fi

# Instalar resto de dependencias en grupos
echo "📦 Instalando FastAPI y dependencias web..."
pip install fastapi uvicorn[standard] pydantic pydantic-settings

echo "📊 Instalando análisis de datos..."
pip install pandas numpy

echo "🤖 Instalando ML ligero..."
pip install scikit-learn xgboost

echo "🌐 Instalando scraping y requests..."
pip install requests beautifulsoup4 aiohttp feedparser

echo "💾 Instalando base de datos..."
pip install sqlalchemy aiosqlite

echo "🛠️ Instalando utilidades..."
pip install python-multipart python-dateutil pytz loguru

echo "✅ Instalación completada!"
echo ""
echo "🚀 Para iniciar el servidor:"
echo "   source venv/bin/activate"
echo "   uvicorn app.main:app --host 0.0.0.0 --port 8000"
echo ""
echo "📝 NOTA: Si PyTorch ocupa mucha memoria, considera usar solo scikit-learn"
