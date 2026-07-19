#!/bin/bash
# Script de prueba rápida para Raspberry Pi

echo "🎯 Probando LoTor Backend en Raspberry Pi..."

# Verificar que estamos en el directorio correcto
if [ ! -f "app/main.py" ]; then
    echo "❌ Error: No estás en el directorio backend/"
    exit 1
fi

# Verificar entorno virtual
if [ ! -d "venv" ]; then
    echo "❌ Error: No existe el entorno virtual"
    echo "   Ejecuta: python3 -m venv venv"
    exit 1
fi

# Activar entorno virtual
source venv/bin/activate

echo "🔍 Verificando dependencias clave..."
python3 -c "
import sys
try:
    import fastapi
    print('✅ FastAPI:', fastapi.__version__)
except:
    print('❌ FastAPI no instalado')
    sys.exit(1)

try:
    import pandas
    print('✅ Pandas:', pandas.__version__)
except:
    print('❌ Pandas no instalado')
    sys.exit(1)

try:
    import sklearn
    print('✅ Scikit-learn:', sklearn.__version__)
except:
    print('⚠️ Scikit-learn no instalado (opcional)')

try:
    import torch
    print('✅ PyTorch:', torch.__version__)
except:
    print('⚠️ PyTorch no instalado (usará modelos ligeros)')

try:
    import xgboost
    print('✅ XGBoost:', xgboost.__version__)
except:
    print('⚠️ XGBoost no instalado (opcional)')

try:
    import loguru
    print('✅ Loguru instalado')
except:
    print('❌ Loguru no instalado')
    sys.exit(1)

print('🎯 Dependencias básicas verificadas')
"

if [ $? -ne 0 ]; then
    echo "❌ Faltan dependencias clave"
    echo "   Instala: pip install -r requirements-arm.txt"
    exit 1
fi

echo ""
echo "🔍 Verificando estructura de archivos..."
required_files=(
    "app/main.py"
    "app/api/predictions.py"
    "app/models/schemas.py"
    "app/services/data_sources.py"
    "app/ml/lightweight_models.py"
    "app/core/model_loader.py"
)

for file in "${required_files[@]}"; do
    if [ -f "$file" ]; then
        echo "✅ $file"
    else
        echo "❌ $file (falta)"
    fi
done

echo ""
echo "🔍 Verificando datos históricos..."
if [ -f "data/raw/primitiva_historical_2026.csv" ]; then
    lines=$(wc -l < data/raw/primitiva_historical_2026.csv)
    echo "✅ Dataset histórico encontrado ($lines líneas)"
else
    echo "⚠️ No hay dataset histórico"
fi

echo ""
echo "🧪 Probando importación de módulos..."
python3 -c "
import sys
sys.path.insert(0, '.')

try:
    from app.core.model_loader import get_model_info
    info = get_model_info()
    print('✅ Model loader funciona')
    print('   Arquitectura:', info['architecture'])
    print('   Modelo:', info['model_type'])
    print('   PyTorch:', info['pytorch_available'])
    print('   Scikit-learn:', info['sklearn_available'])
except Exception as e:
    print('❌ Error en model loader:', e)
    sys.exit(1)

try:
    from app.ml.lightweight_models import create_statistical_model
    model = create_statistical_model()
    print('✅ Modelos ligeros funcionan')
except Exception as e:
    print('❌ Error en modelos ligeros:', e)
    sys.exit(1)

print('🎯 Todos los módulos importan correctamente')
"

if [ $? -ne 0 ]; then
    echo "❌ Error en importación de módulos"
    exit 1
fi

echo ""
echo "🚀 Iniciando servidor de prueba..."
echo "   Presiona Ctrl+C para detener"
echo ""

timeout 10s uvicorn app.main:app --host 127.0.0.1 --port 8000 > /tmp/lotor_test.log 2>&1 &
SERVER_PID=$!

# Esperar a que el servidor inicie
sleep 3

if ps -p $SERVER_PID > /dev/null; then
    echo "✅ Servidor inició correctamente (PID: $SERVER_PID)"

    # Probar endpoint de health
    echo "🔍 Probando endpoint /health..."
    response=$(curl -s http://127.0.0.1:8000/health)
    if echo "$response" | grep -q "healthy"; then
        echo "✅ Health check funcionando"
    else
        echo "❌ Health check falló"
    fi

    # Probar endpoint de modelos
    echo "🔍 Probando endpoint /predictions/models/status..."
    response=$(curl -s http://127.0.0.1:8000/api/v1/predictions/models/status)
    if echo "$response" | grep -q "model_type"; then
        echo "✅ Status endpoint funcionando"
        echo "$response" | python3 -m json.tool 2>/dev/null || echo "$response"
    else
        echo "❌ Status endpoint falló"
    fi

    # Detener servidor
    echo ""
    echo "🛑 Deteniendo servidor..."
    kill $SERVER_PID 2>/dev/null
    wait $SERVER_PID 2>/dev/null

    echo "✅ Prueba completada exitosamente"
    echo ""
    echo "🎱 Para usar el sistema:"
    echo "   source venv/bin/activate"
    echo "   uvicorn app.main:app --host 0.0.0.0 --port 8000"
    echo "   Accede a: http://localhost:8000/docs"

else
    echo "❌ El servidor no inició correctamente"
    echo "   Revisa /tmp/lotor_test.log para detalles"
    cat /tmp/lotor_test.log
    exit 1
fi
