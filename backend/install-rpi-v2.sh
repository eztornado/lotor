#!/bin/bash
# Script de instalación DEFINITIVO para Raspberry Pi (SIN PyTorch)

echo "🎯 Instalando LoTor Backend para Raspberry Pi 3 (SIN PyTorch)"
echo "⚡ Usando scikit-learn + XGBoost (ARM compatible)"

# Verificar que estamos en el directorio correcto
if [ ! -f "app/main.py" ]; then
    echo "❌ Error: No estás en el directorio backend/"
    exit 1
fi

# Activar entorno virtual si existe
if [ -d "venv" ]; then
    echo "🐍 Activando entorno virtual existente..."
    source venv/bin/activate
else
    echo "🐍 Creando nuevo entorno virtual..."
    python3 -m venv venv
    source venv/bin/activate
fi

# Actualizar pip
echo "📦 Actualizando pip..."
pip install --upgrade pip setuptools wheel

# Instalar dependencias en orden correcto
echo "📊 Instalando FastAPI y dependencias web..."
pip install fastapi uvicorn[standard] pydantic pydantic-settings

echo "🔢 Instalando análisis de datos..."
pip install pandas numpy

echo "🤖 Instalando Machine Learning (ARM compatible)..."
pip install scikit-learn xgboost

echo "🌐 Instalando scraping y requests..."
pip install requests beautifulsoup4 aiohttp feedparser

echo "💾 Instalando base de datos..."
pip install sqlalchemy aiosqlite

echo "🛠️ Instalando utilidades..."
pip install python-multipart python-dateutil pytz loguru

echo "✅ Instalación completada!"
echo ""
echo "📋 Paquetes instalados:"
pip list | grep -E "(fastapi|scikit-learn|xgboost|pandas|numpy|uvicorn)"
echo ""
echo "🚀 Para iniciar el servidor:"
echo "   source venv/bin/activate"
echo "   uvicorn app.main:app --host 0.0.0.0 --port 8000"
echo ""
echo "📝 NOTA: Sistema usará modelos ligeros (scikit-learn) en lugar de PyTorch"
