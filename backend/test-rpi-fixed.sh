#!/bin/bash
# Test LoTor en Raspberry Pi - Version CORREGIDA
# Usa scikit-learn en lugar de sklearn

set -e

echo "=== LoTor - Test Completo ==="
echo ""

cd /root/LoTor/backend

if [ ! -d "venv" ]; then
    echo "❌ ERROR: venv no encontrado. Ejecuta install-rpi-final.sh primero"
    exit 1
fi

source venv/bin/activate

echo "1/8 Verificando dependencias core..."
python -c "import fastapi, uvicorn, pydantic; print('   ✓ Core OK')"

echo ""
echo "2/8 Verificando numpy (versión precompilada ARM)..."
python -c "import numpy; print(f'   ✓ NumPy {numpy.__version__}')"

echo ""
echo "3/8 Verificando scikit-learn (scikit-learn, no sklearn)..."
python -c "import sklearn; print(f'   ✓ scikit-learn {sklearn.__version__}')"

echo ""
echo "4/8 Verificando XGBoost..."
python -c "import xgboost; print(f'   ✓ XGBoost {xgboost.__version__}')"

echo ""
echo "5/8 Verificando pandas..."
python -c "import pandas; print(f'   ✓ pandas {pandas.__version__}')"

echo ""
echo "6/8 Verificando módulos ML..."
python -c "
import sys
sys.path.insert(0, '/root/LoTor')
from app.ml.lightweight_models import LightweightPredictor
from app.ml.multi_combination_light import MultiCombinationGeneratorLight
print('   ✓ Módulos ML cargados OK')
"

echo ""
echo "7/8 Verificando detector de arquitectura..."
python -c "
import sys
sys.path.insert(0, '/root/LoTor')
from app.core.model_loader import get_best_model_type
model_type = get_best_model_type()
print(f'   ✓ Modelo detectado: {model_type}')
if model_type != 'lightweight':
    print('   ⚠️  Advertencia: Debería ser \"lightweight\" en ARM')
"

echo ""
echo "8/8 Generando combinaciones de prueba..."
python -c "
import sys
sys.path.insert(0, '/root/LoTor')

# Crear generador
from app.ml.multi_combination_light import MultiCombinationGeneratorLight
gen = MultiCombinationGeneratorLight()

# Cargar datos
import pandas as pd
csv_path = '/root/LoTor/backend/data/raw/primitiva_historical_2026.csv'
df = pd.read_csv(csv_path)

# Generar combinaciones
combinations = gen.generate_all_combinations(df)

print(f'   ✓ {len(combinations)} combinaciones generadas:')
for i, combo in enumerate(combinations, 1):
    print(f'     {i}. {combo[\"strategy\"]}: {combo[\"numbers\"]} + {combo[\"key_number\"]}')
"

echo ""
echo "=== ✅ TODOS LOS TESTS PASARON ==="
echo ""
echo "Sistema listo para usar. Ejecuta:"
echo "  source venv/bin/activate"
echo "  uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
