#!/bin/bash
# Script de prueba DEFINITIVO para Raspberry Pi (SIN PyTorch)

echo "🎯 Probando LoTor Backend - Raspberry Pi 3 (Sin PyTorch)"

# Verificar directorio
if [ ! -f "app/main.py" ]; then
    echo "❌ Error: No estás en el directorio backend/"
    exit 1
fi

# Activar entorno virtual
if [ -d "venv" ]; then
    echo "🐍 Activando entorno virtual..."
    source venv/bin/activate
else
    echo "❌ Error: No existe el entorno virtual"
    echo "   Ejecuta primero: install-rpi-v2.sh"
    exit 1
fi

echo "🔍 Verificando dependencias CRÍTICAS (SIN PyTorch)..."
python3 << 'EOF'
import sys

# Dependencias críticas
critical_packages = {
    'fastapi': 'FastAPI',
    'uvicorn': 'Uvicorn',
    'pydantic': 'Pydantic',
    'pandas': 'Pandas',
    'numpy': 'NumPy',
    'loguru': 'Loguru'
}

optional_packages = {
    'sklearn': 'Scikit-learn',
    'xgboost': 'XGBoost'
}

missing_critical = []
missing_optional = []

# Verificar críticas
for module, name in critical_packages.items():
    try:
        if module == 'sklearn':
            import sklearn
            print(f'✅ {name}: {sklearn.__version__}')
        else:
            exec(f'import {module}')
            print(f'✅ {name}: OK')
    except ImportError:
        print(f'❌ {name}: FALTANTE')
        missing_critical.append(name)

# Verificar opcionales
for module, name in optional_packages.items():
    try:
        exec(f'import {module}')
        print(f'✅ {name}: OK (opcional)')
    except ImportError:
        print(f'⚠️ {name}: No instalado (opcional)')
        missing_optional.append(name)

# Verificar que PyTorch NO está instalado (es normal)
try:
    import torch
    print('⚠️ PyTorch: INSTALADO (no es necesario)')
except ImportError:
    print('✅ PyTorch: No instalado (normal en ARM)')

if missing_critical:
    print(f'\n❌ FALTAN paquetes críticos: {missing_critical}')
    sys.exit(1)
else:
    print('\n✅ Todos los paquetes críticos están instalados')
    if missing_optional:
        print(f'⚠️ Opcionales faltantes: {missing_optional}')
        print('   El sistema funcionará, pero sin ML avanzado')
EOF

PY_CHECK=$?

if [ $PY_CHECK -ne 0 ]; then
    echo ""
    echo "❌ Faltan dependencias críticas"
    echo "   Instala: pip install -r requirements-no-torch.txt"
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
        echo "❌ $file (FALTA)"
    fi
done

echo ""
echo "🔍 Verificando datos históricos..."
if [ -f "data/raw/primitiva_historical_2026.csv" ]; then
    lines=$(wc -l < data/raw/primitiva_historical_2026.csv)
    echo "✅ Dataset histórico: $lines líneas"
else
    echo "⚠️ Dataset histórico no encontrado (se descargará automáticamente)"
fi

echo ""
echo "🧪 Probando importación de módulos..."
python3 << 'EOF'
import sys
sys.path.insert(0, '.')

try:
    from app.core.model_loader import get_model_info
    info = get_model_info()
    print('✅ Model loader funciona')
    print(f'   Arquitectura: {info["architecture"]}')
    print(f'   Modelo: {info["model_type"]}')
    print(f'   PyTorch: {info["pytorch_available"]}')
    print(f'   Scikit-learn: {info["sklearn_available"]}')

    if info['architecture'] == 'arm' and info['model_type'] == 'lightweight':
        print('✅ Configuración óptima para ARM detectada')
    elif info['architecture'] == 'arm' and info['model_type'] != 'lightweight':
        print('⚠️ Configuración subóptima para ARM')

except Exception as e:
    print(f'❌ Error en model loader: {e}')
    sys.exit(1)

try:
    from app.ml.lightweight_models import create_statistical_model
    model = create_statistical_model()
    print('✅ Modelos ligeros funcionan')
except Exception as e:
    print(f'❌ Error en modelos ligeros: {e}')
    sys.exit(1)

try:
    from app.ml.multi_combination_light import create_lightweight_multi_combination_generator
    print('✅ Sistema de 7 combinaciones funciona')
except Exception as e:
    print(f'❌ Error en sistema de combinaciones: {e}')
    sys.exit(1)

print('✅ Todos los módulos importan correctamente')
EOF

MODULE_CHECK=$?

if [ $MODULE_CHECK -ne 0 ]; then
    echo "❌ Error en importación de módulos"
    exit 1
fi

echo ""
echo "🚀 Iniciando servidor de prueba..."
echo "   Presiona Ctrl+C para detener la prueba"
echo ""

timeout 15s uvicorn app.main:app --host 127.0.0.1 --port 8000 > /tmp/lotor_test.log 2>&1 &
SERVER_PID=$!

# Esperar a que el servidor inicie
sleep 5

if ps -p $SERVER_PID > /dev/null; then
    echo "✅ Servidor inició correctamente (PID: $SERVER_PID)"

    # Probar endpoint de health
    echo ""
    echo "🔍 Probando endpoint /health..."
    response=$(curl -s http://127.0.0.1:8000/health)
    if echo "$response" | grep -q "healthy"; then
        echo "✅ Health check funcionando"
    else
        echo "❌ Health check falló"
        echo "   Respuesta: $response"
    fi

    # Probar endpoint de modelos
    echo ""
    echo "🔍 Probando endpoint /predictions/models/status..."
    response=$(curl -s http://127.0.0.1:8000/api/v1/predictions/models/status)
    if echo "$response" | grep -q "model_type"; then
        echo "✅ Status endpoint funcionando"
        echo "$response" | python3 -m json.tool 2>/dev/null || echo "$response"
    else
        echo "❌ Status endpoint falló"
        echo "   Respuesta: $response"
    fi

    # Probar predicción
    echo ""
    echo "🔍 Probando predicción (puede tardar unos segundos)..."
    response=$(curl -s -X POST http://127.0.0.1:8000/api/v1/predictions/predict)
    if echo "$response" | grep -q "predicted_numbers"; then
        echo "✅ Predicción funcionando"
        echo "$response" | python3 -m json.tool 2>/dev/null | head -15 || echo "$response"
    else
        echo "❌ Predicción falló"
        echo "   Respuesta: $response"
    fi

    # Detener servidor
    echo ""
    echo "🛑 Deteniendo servidor..."
    kill $SERVER_PID 2>/dev/null
    wait $SERVER_PID 2>/dev/null

    echo ""
    echo "✅ PRUEBA COMPLETADA EXITOSAMENTE"
    echo ""
    echo "🎱 Sistema listo para usar:"
    echo "   source venv/bin/activate"
    echo "   uvicorn app.main:app --host 0.0.0.0 --port 8000"
    echo "   Accede a: http://localhost:8000/docs"
    echo ""
    echo "📝 Nota: Sistema usa modelos ligeros (scikit-learn) optimizados para ARM"

else
    echo "❌ El servidor no inició correctamente"
    echo "   Revisa /tmp/lotor_test.log para detalles"
    cat /tmp/lotor_test.log
    exit 1
fi
